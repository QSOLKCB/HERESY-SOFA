def createBinaryTree(self, descriptions):
    nodes, children = {}, set()
    for p, c, is_left in descriptions:
        P = nodes.setdefault(p, TreeNode(p))
        C = nodes.setdefault(c, TreeNode(c))
        if is_left: P.left = C
        else:       P.right = C
        children.add(c)
    # the root is the one parent that is never a child
    return nodes[next(p for p, _, _ in descriptions if p not in children)]
