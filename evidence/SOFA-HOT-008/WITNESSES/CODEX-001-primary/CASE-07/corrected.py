from original import TreeNode


def create_binary_tree(descriptions):
    nodes = {}
    parents = set()
    children = set()
    for parent_value, child_value, is_left in descriptions:
        if parent_value not in nodes:
            nodes[parent_value] = TreeNode(parent_value)
        if child_value not in nodes:
            nodes[child_value] = TreeNode(child_value)
        parent = nodes[parent_value]
        child = nodes[child_value]
        if is_left:
            parent.left = child
        else:
            parent.right = child
        parents.add(parent_value)
        children.add(child_value)
    root_values = parents - children
    if len(root_values) != 1:
        raise ValueError("descriptions must identify exactly one root")
    return nodes[root_values.pop()], nodes
