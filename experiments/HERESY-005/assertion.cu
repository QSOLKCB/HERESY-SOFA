#include <cassert>
#include <cstdio>
#include <cstring>

#include <cuda_runtime.h>

__global__ void controlled_assertion(int condition) {
    assert(condition);
}

static int probe_device() {
    int driver_version = 0;
    int runtime_version = 0;
    int device_count = 0;
    cudaError_t driver_status = cudaDriverGetVersion(&driver_version);
    cudaError_t runtime_status = cudaRuntimeGetVersion(&runtime_version);
    cudaError_t count_status = cudaGetDeviceCount(&device_count);

    if (driver_status != cudaSuccess || runtime_status != cudaSuccess ||
        count_status != cudaSuccess || device_count < 1) {
        std::printf(
            "{\"driver_status\":%d,\"runtime_status\":%d,"
            "\"device_count_status\":%d,\"device_count\":%d,"
            "\"driver_version\":%d,\"runtime_version\":%d}\n",
            static_cast<int>(driver_status), static_cast<int>(runtime_status),
            static_cast<int>(count_status), device_count, driver_version,
            runtime_version);
        return 30;
    }

    cudaDeviceProp properties{};
    cudaError_t properties_status = cudaGetDeviceProperties(&properties, 0);
    if (properties_status != cudaSuccess) {
        std::printf(
            "{\"driver_status\":%d,\"runtime_status\":%d,"
            "\"device_count_status\":%d,\"device_count\":%d,"
            "\"properties_status\":%d}\n",
            static_cast<int>(driver_status), static_cast<int>(runtime_status),
            static_cast<int>(count_status), device_count,
            static_cast<int>(properties_status));
        return 31;
    }

    std::printf(
        "{\"driver_status\":%d,\"runtime_status\":%d,"
        "\"device_count_status\":%d,\"device_count\":%d,"
        "\"properties_status\":%d,\"driver_version\":%d,"
        "\"runtime_version\":%d,\"gpu_name\":\"%s\","
        "\"compute_capability\":\"%d.%d\"}\n",
        static_cast<int>(driver_status), static_cast<int>(runtime_status),
        static_cast<int>(count_status), device_count,
        static_cast<int>(properties_status), driver_version, runtime_version,
        properties.name, properties.major, properties.minor);
    return 0;
}

static int run_assertion(bool fault) {
    controlled_assertion<<<1, 1>>>(fault ? 0 : 1);
    cudaError_t launch_status = cudaGetLastError();

    // Once cudaErrorAssert is observed, make no further CUDA calls in this
    // process.  The parent records the skipped synchronization explicitly.
    if (launch_status == cudaErrorAssert) {
        std::printf(
            "{\"mode\":\"%s\",\"launch_status\":%d,"
            "\"synchronize_status\":null,"
            "\"synchronize_skipped_after_assert\":true}\n",
            fault ? "fault" : "control", static_cast<int>(launch_status));
        return fault ? 10 : 20;
    }

    if (launch_status != cudaSuccess) {
        std::printf(
            "{\"mode\":\"%s\",\"launch_status\":%d,"
            "\"synchronize_status\":null,"
            "\"synchronize_skipped_after_launch_error\":true}\n",
            fault ? "fault" : "control", static_cast<int>(launch_status));
        return 21;
    }

    cudaError_t synchronize_status = cudaDeviceSynchronize();
    // Deliberately do not query, reset, allocate, launch, or synchronize again
    // after this call.  In the fault case the CUDA context may be poisoned.
    std::printf(
        "{\"mode\":\"%s\",\"launch_status\":%d,"
        "\"synchronize_status\":%d,"
        "\"synchronize_skipped_after_assert\":false}\n",
        fault ? "fault" : "control", static_cast<int>(launch_status),
        static_cast<int>(synchronize_status));

    if (!fault) {
        return synchronize_status == cudaSuccess ? 0 : 20;
    }
    return synchronize_status == cudaErrorAssert ? 10 : 22;
}

int main(int argc, char **argv) {
    if (argc == 2 && std::strcmp(argv[1], "--probe") == 0) {
        return probe_device();
    }
    if (argc == 3 && std::strcmp(argv[1], "--mode") == 0) {
        if (std::strcmp(argv[2], "control") == 0) {
            return run_assertion(false);
        }
        if (std::strcmp(argv[2], "fault") == 0) {
            return run_assertion(true);
        }
    }
    std::fprintf(stderr, "usage: assertion --probe | --mode control|fault\n");
    return 2;
}
