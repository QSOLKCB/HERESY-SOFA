def build(descriptions, TreeNode):
    nodes, children = {}, set()
    for p,c,is_left in descriptions:
        if p not in nodes: nodes[p]=TreeNode(p)
        if c not in nodes: nodes[c]=TreeNode(c)
        if is_left: nodes[p].left=nodes[c]
        else: nodes[p].right=nodes[c]
        children.add(c)
    return nodes[next(p for p,_,_ in descriptions if p not in children)]
