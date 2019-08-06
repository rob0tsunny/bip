import ida_hexrays
import ida_kernwin

from hx_lvar import HxLvar
from hx_visitor import _hx_visitor_expr, _hx_visitor_list_expr, _hx_visitor_stmt, _hx_visitor_list_stmt, _hx_visitor_all, _hx_visitor_list_all
from cnode import CNode
from cnode_visitor import visit_dfs_cnode, visit_dfs_cnode_filterlist

class HxCFunc(object):
    """
        Python object for representing a C function as decompile by hexrays.
        This is an abstraction on top of the ``ida_hexrays.cfuncptr_t``  and
        ``cfunc_t`` object.

        .. warning::
        
            Decompiling again the function in hexrays (meaning
            hitting F5 again) will create a new ``cfunc_t`` object. An
            :class:`HxCFunc` python object (or the corresponding ``cfunc_t``
            object from IDA) and the others associated objects (such as the 
            :class:`HxLvar` for example) will not be the same anymore. This
            can create problems when using the scripting and the interactive
            view at the same time. Basically you will want to regenerate this
            object for the function each time you make F5 again in the GUI,
            this can be done using the :meth:`HxCFunc.from_addr` class method.

        .. todo:: support everything

            * Comments (cfuncp.user_cmts)

        .. todo:: type

        .. todo:: everything in ``cfunc_t`` .

        .. todo:: make smart? error for when ida_hexrays api does not exist

        .. todo:: pretty printer

        .. todo:: make a function for recuperating a lvar from a register or a stack
            location

        .. todo:: test
    """

    def __init__(self, cfunc):
        """
            Constructor for a :class:`HxCFunc` object.

            .. todo:: test

            :param cfunc: A ``cfunc_t`` pointer from IDA object such as return
                by ``ida_hexrays.decompile`` .
        """
        self._cfunc = cfunc

    @property
    def ea(self):
        """
            Property which return the start address of this function.

            .. todo:: test

            :return int: The start address of this function
        """
        return self._cfunc.entry_ea


    @property
    def cstr(self):
        """
            Property which return the C code corresponding to the
            decompilation of this function.

            :return str: The string corresponding to the decompilation of this
                function.
        """
        return str(self._cfunc)

    ################################ CMT ###########################

    def add_cmt(self, ea, value, itp=69):
        """
            Allow to add a comment in the hexrays interface view. 

            .. todo: doc & better (in particular itp)

            :param int ea: The address at which add the comment. All ea
                address in the function will not be valid, only the one used
                for items in the ctree seems to be. 
            :param str value: The comment value.
            :param int itp: The position at which add the comment
                (item_tree_position todo).
        """
        tl = ida_hexrays.treeloc_t()
        tl.ea = ea
        tl.itp = itp
        self._cfunc.set_user_cmt(tl, value)
        self._cfunc.save_user_cmts()
        

    ################################ LVARS ###################################

    def lvar_at(self, idx):
        """
            Return the local variable corresponding to an index.

            This equivalent to using :meth:`~HxCFunc.lvars` with access in an
            index but should be faster.
            
            :return: A :class:`HxLvar` object.
        """
        return HxLvar(self._cfunc.lvars[idx], self)

    @property
    def lvars(self):
        """
            Return a list of :class:`HxLvar` object representing the local
            variables of this function. This function will return the argument
            as well as the local variable of the function.

            .. todo:: test

            :return: A list of :class:`HxLvar`.
        """
        return [HxLvar(l, self) for l in self._cfunc.get_lvars()]

    @property
    def lvars_iter(self):
        """
            Return an iterator of :class:`HxLvar` object representing the
            local variables of this function. This is similar to
            :meth:`~HxCFunc.lvars` but with an iterator instead of a list.

            .. todo:: test

            :return: An interator of :class:`HxLvar`.
        """
        for l in self._cfunc.get_lvars():
            yield HxLvar(l, self)

    @property
    def args(self):
        """
            Return a list of :class:`HxLvar` object representing the argument
            of this functions.

            .. todo:: test

            :return: A list of :class:`HxLvar`.
        """
        return [HxLvar(l, self) for l in self._cfunc.get_lvars() if l.is_arg_var]

    ############################ CNODE & VISITORS ############################

    @property
    def root_node(self):
        """
            Property which return the :class:`CNode` object which is the root
            element for
            this function. This :class:`CNode` will allow to visit the AST of
            the function. In practice it should always be of
            class :class:`CNodeStmtBlock` .

            :return: The root object for this function which inherit from
                :class:`CNode` .
        """
        return CNode.GetCNode(self._cfunc.body, self, None)

    def visit_cnode(self, callback):
        """
            Method which allow to visit all :class:`CNode` elements of this
            function starting from the root object. This is implemented using
            a DFS algorithm. This does not use the hexrays visitor. For more
            information about the implementation see
            :func:`~cnode_visitor.visit_dfs_cnode` (this method is just a
            wrapper).

            :param callback: A callable which will be called on all
                :class:`CNode` in the function decompiled by hexrays. The call
                should take only one argument which correspond to the
                :class:`CNode` currently visited.
        """
        visit_dfs_cnode(self.root_node, callback)

    def visit_cnode_filterlist(self, callback, filter_list):
        """
            Method which allow to visit :class:`CNode` elements which are
            present in a list. This is implemented using
            a DFS algorithm. This does not use the hexrays visitor. For more
            information about the implementation see
            :func:`~cnode_visitor.visit_dfs_cnode_filterlist` (this method is just
            a wrapper).

            :param callback: A callable which will be called on all
                :class:`CNode` in the function decompiled by hexrays. The call
                should take only one argument which correspond to the
                :class:`CNode` currently visited.
            :param filter_list: A list of class which inherit from :class:`CNode`.
                The callback will be called only for the node from a class in this
                list.
        """
        visit_dfs_cnode_filterlist(self.root_node, callback, filter_list)

    def get_cnode_filter(self, cb_filter):
        """
            Method which return a list of :class:`CNode` for which a filter
            return true. Internally this use the :meth:`~HxCFunc.visit_cnode`
            method which visit all nodes of the function, this is just a
            usefull wrapper.

            :param cb_filter: A callable which take a :class:`CNode` in
                parameter and return a boolean. This callback will be called
                on all node of the function and all node for which it returns
                true will be added in a list which will be returned by this
                function.
            :return: A list of :class:`CNode` which have match the filter.
                This list is order in which the node have been visited (see
                :meth:`~HxCFunc.visit_cnode` for more information).
        """
        l = []
        def _app_filt(cn):
            if cb_filter(cn):
                l.append(cn)
        self.visit_cnode(_app_filt)
        return l

    ############################ HX VISITOR METHODS ##########################

# todo: 
# * indicated as deprecated or that it should use bip visitors
# * make examples ?

    def hx_visit_generic(self, visitor_class, *args):
        """
            Generic method for creating and calling the hexrays visitors on
            this function. This function is used by the other ``hx_visit_*``
            functions for using the hexrays visitor. The goal of this
            funcction  is also to allow to integrated existing IDA visitor.

            :param visitor_class: A class which inherit from the IDA
                ``ctree_visitor_t`` class.
            :param args: Argument which will be passed to the constructor of
                the ``visitor_class`` .
        """
        v = visitor_class(*args)
        v.apply_to(self._cfunc.body, None)

    def hx_visit_expr(self, func_visit):
        """
            Allow to use the hexrays visitor for visiting all expressions
            (:class:`HxCExpr`) of this function.

            Internally this function use the :class:`_hx_visitor_expr`
            visitor.

            :param func_visit: A function which take as argument an
                :class:`HxCExpr` object. This function will be called on all
                :class:`HxCExpr` element which are part of this function.
        """
        self.hx_visit_generic(_hx_visitor_expr, func_visit)

    def hx_visit_list_expr(self, expr_list, func_visit):
        """
            Allow to use the hexrays visitor for visiting only expressions
            (:class:`HxCExpr`) which are part of a list.

            .. code-block:: python

                # example which print all the HxCExprCall from the function
                # hxf is an object of this class HxCFunc.
                def fu(e):
                    print(e)

                hxf.visit_list_expr([HxCExprCall], fu)

            Internally this function use the :class:`_hx_visitor_list_expr`
            visitor.

            :param expr_list: A list of class which inherit from
                :class:`HxCExpr`, only expression in the list will be visited.
            :param func_visit: A function which take as argument an
                :class:`HxCExpr` object. This function will be called on all
                element which are in the ``expr_list`` .
        """
        self.hx_visit_generic(_hx_visitor_list_expr, expr_list, func_visit)

    def hx_visit_stmt(self, func_visit):
        """
            Allow to use the hexrays visitor for visiting all statements
            (:class:`HxCStmt`) of this function.

            Internally this function use the :class:`_hx_visitor_stmt`
            visitor.

            :param func_visit: A function which take as argument an
                :class:`HxCStmt` object. This function will be called on all
                :class:`HxCStmt` element which are part of this function.
        """
        self.hx_visit_generic(_hx_visitor_stmt, func_visit)

    def hx_visit_list_stmt(self, stmt_list, func_visit):
        """
            Allow to use the hexrays visitor for visiting only statements
            (:class:`HxCStmt`) which are part of a list.

            Internally this function use the :class:`_hx_visitor_list_stmt`
            visitor.

            :param stmt_list: A list of class which inherit from
                :class:`HxCStmt`, only statements in the list will be visited.
            :param func_visit: A function which take as argument an
                :class:`HxCStmt` object. This function will be called on all
                element which are in the ``stmt_list`` .
        """
        self.hx_visit_generic(_hx_visitor_list_stmt, stmt_list, func_visit)

    def hx_visit_all(self, func_visit):
        """
            Allow to use the hexrays visitor for visiting all items
            (statements :class:`HxCStmt` and expression :class:`HxCExpr`) of
            this function.

            Internally this function use the :class:`_hx_visitor_all`
            visitor.

            :param func_visit: A function which take as argument an object
                which inherit from :class:`HxCItem`. This function will be
                called on all those elements which are part of this function.
        """
        self.hx_visit_generic(_hx_visitor_all, func_visit)

    def hx_visit_list_all(self, item_list, func_visit):
        """
            Allow to use the hexrays visitor for visiting only statements
            (:class:`HxCStmt`) which are part of a list.
            Allow to use the hexrays visitor for visiting only items
            (statements :class:`HxCStmt` and expression :class:`HxCExpr`)
            which are part of a list.

            Internally this function use the :class:`_hx_visitor_list_all`
            visitor.

            :param item_list: A list of class which inherit from
                :class:`HxCItem`, only items in the list will be visited.
            :param func_visit: A function which take as argument an
                :class:`HxCItem` object. This function will be called on all
                element which are in the ``item_list`` .
        """
        self.hx_visit_generic(_hx_visitor_list_all, item_list, func_visit)

    ############################### CLASS METHOD ############################

    @classmethod
    def from_addr(cls, ea=None):
        """
            Class method which return a :class:`HxFunc` object corresponding
            to the function at a particular address.

            .. todo:: error handling

            .. todo:: test

            :param int ea: An address inside the function for which we want
                an :class:`HxFunc`. If ``None`` the screen address will be
                used.
            :return: A :class:`HxFunc` object.
        """
        if ea is None:
            ea = ida_kernwin.get_screen_ea()
        return cls(ida_hexrays.decompile(ea))


