from original import TreeNode


def create_with_setdefault(descriptions):
    nodes, children = {}, set()
    for p, c, is_left in descriptions:
        parent = nodes.setdefault(p, TreeNode(p))
        child = nodes.setdefault(c, TreeNode(c))
        if is_left:
            parent.left = child
        else:
            parent.right = child
        children.add(c)
    return nodes[next(p for p, _, _ in descriptions if p not in children)], nodes
