import itertools
from collections import defaultdict

import numpy as np
import networkx as nx

from pgmpy.factors import TabularCPD, TreeCPD, RuleCPD
from pgmpy.base import DirectedGraph, UndirectedGraph


class DynamicBayesianNetwork(DirectedGraph):
    def __init__(self, ebunch=None):
        """
        Base class for Dynamic Bayesian Network

        This model is a time variant of the static Bayesian model, where each
        time-slice has some static nodes and is then replicated over a certain
        time-slice.

        The nodes can be any hashable python objects.

        Parameters:
        ----------
        ebunch: Data to initialize graph.  If data=None (default) an empty
              graph is created.  The data can be an edge list, or any NetworkX
              graph object

        Examples:
        --------
        Create an empty Dynamic Bayesian Network with no nodes and no edges
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN()

        Adding nodes and edges inside the dynamic bayesian network. A single
        node can be added using the method below. For adding edges we need to
        specify the time slice since edges can be across different time slices.

        >>> dbn.add_nodes_from(['D','G','I','S','L'])
        >>> dbn.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('G',0),('L',0))])

        >>> dbn.nodes()
        ['L', 'G', 'S', 'I', 'D']
        >>> dbn.edges()
        [(('D', 0), ('G', 0)), (('G', 0), ('L', 0)), (('I', 0), ('G', 0))]

        If any variable is not present in the network while adding an edge,
        pgmpy will automatically add that variable to the network.


        Public Methods:
        ---------------
        add_cpds
        add_edge
        add_edges_from
        add_node
        add_nodes_from
        initialize_initial_state
        inter_slice
        intra_slice
        """
        super().__init__()
        if ebunch:
            self.add_edges_from(ebunch)
        self.cpds = []
        self.cardinalities = defaultdict(int)

    def add_node(self, node, **attr):
        """
        Adds a single node to the Network

        Parameters
        ----------
        node: node
            A node can be any hashable Python object.

        Examples
        --------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN()
        >>> dbn.add_node('A')
        """
        super().add_node((node, 0), **attr)

    def add_nodes_from(self, nodes, **attr):
        """
        Add multiple nodes to the Network.

        Parameters
        ----------
        nodes: iterable container
            A container of nodes (list, dict, set, etc.).

        Examples
        --------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN()
        >>> dbn.add_nodes_from(['A', 'B', 'C'])
        """
        for node in nodes:
            self.add_node(node)

    def nodes(self):
        """
        Returns the list of nodes present in the network

        Examples
        --------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN()
        >>> dbn.add_nodes_from(['A', 'B', 'C'])
        >>> dbn.nodes()
        ['B', 'A', 'C']
        """
        return list(set([node for node, timeslice in super().nodes()]))

    def add_edge(self, start, end, **kwargs):
        """
        Add an edge between two nodes.

        The nodes will be automatically added if they are not present in the network.

        Parameters
        ----------
        start, end: The start, end nodes should contain the (node_name, time_slice)
                    Here, node_name can be a hashable python object while the
                    time_slice is an integer value, which denotes the index of the
                    time_slice that the node belongs to.

        Examples
        --------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> model = DBN()
        >>> model.add_nodes_from(['D', 'I'])
        >>> model.add_edge(('D',0), ('I',0))
        >>> model.edges()
        [(('D', 1), ('G', 1)), (('D', 0), ('G', 0))]
        """
        try:
            if len(start) != 2 or len(end) !=2:
                raise ValueError('Nodes must be of type (node, time_slice).')
            elif not isinstance(start[1], int) or not isinstance(end[1], int):
                raise ValueError('Nodes must be of type (node, time_slice).')
            elif start[1] == end[1]:
                start = (start[0], 0)
                end = (end[0], 0)
            elif start[1] == end[1] - 1:
                start = (start[0], 0)
                end = (end[0], 1)
            elif start[1] == end[1] + 1:
                raise ValueError('Edges in backward direction are not allowed.')
            elif start[1] != end[1]:
                raise ValueError("Edges over multiple time slices is not currently supported")
        except TypeError:
            raise ValueError('Nodes must be of type (node, time_slice).')

        if start == end:
            raise ValueError('Self Loops are not allowed')
        elif start in super().nodes() and end in super().nodes() and nx.has_path(self, end, start):
            raise ValueError(
                 'Loops are not allowed. Adding the edge from (%s->%s) forms a loop.' % (str(end), str(start)))

        super().add_edge(start, end, **kwargs)

        if start[1] == end[1]:
            super().add_edge((start[0], 1 - start[1]), (end[0], 1 - end[1]))

    def add_edges_from(self, ebunch, **kwargs):
        """
        Add all the edges in ebunch.
        If nodes referred in the ebunch are not already present, they
        will be automatically added. Node names should be strings.
        Parameters
        ----------
        ebunch : container of edges
            Each edge given in the container will be added to the graph.
            The edges must be given as 2-tuples (u, v).
        Examples
        --------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN()
        >>> dbn.add_edges_from([(('D',0), ('G',0)), (('I',0), ('G',0))])
        """
        for edge in ebunch:
            self.add_edge(edge[0], edge[1])

    def get_intra_edges(self, time_slice=0):
        """
        returns the intra slice edges present in the 2-TBN.
        Parameter
        ---------
        time_slice:int 
                   The timeslice should be a positive value greater than or equal to zero

        Examples:
        -------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN()
        >>> dbn.add_nodes_from(['D','G','I','S','L'])
        >>> dbn.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('G',0),('L',0)),(('D',0),('D',1))])
        >>> dbn.get_intra_edges()
        [(('D', 0), ('G', 0)), (('G', 0), ('L', 0)), (('I', 0), ('G', 0))
        """
        if not isinstance(time_slice, int) or time_slice < 0:
            raise ValueError("The timeslice should be a positive value greater than or equal to zero")

        return [tuple((x[0], time_slice) for x in edge) for edge in self.edges() if edge[0][1] == edge[1][1] == 0]

    def get_inter_edges(self):
        """
        returns the inter-slice edges present in the 2-TBN
        Examples:
        -------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN()
        >>> dbn.add_nodes_from(['D','G','I','S','L'])
        >>> dbn.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('D',0),('D',1)),(('I',0),('I',1)))])
        >>> dbn.get_inter_edges()
        [(('D', 0), ('D', 1)), (('I', 0), ('I', 1))]
        """
        return [edge for edge in self.edges() if edge[0][1] != edge[1][1]]

    def get_interface_nodes(self, time_slice=0):
    	"""
    	returns the nodes in the first timeslice whose children are present in the first timeslice.
        Parameter
        ---------
        time_slice:int 
                   The timeslice should be a positive value greater than or equal to zero

    	Examples:
    	-------
    	>>> from pgmpy.models import DynamicBayesianNetwork as DBN
    	>>> dbn = DBN()
    	>>> dbn.add_nodes_from(['D', 'G', 'I', 'S', 'L'])
    	>>> dbn.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('G',0),('L',0)),(('D',0),('D',1))])
    	>>> dbn.get_interface_nodes()
    	[('D', 0)]
    	"""
    	if not isinstance(time_slice, int) or time_slice < 0:
            raise ValueError("The timeslice should be a positive value greater than or equal to zero")

    	return [(edge[0][0], time_slice) for edge in self.get_inter_edges()]

    def get_slice_nodes(self, time_slice=0):
    	"""
    	returns the nodes present in a particular timeslice
        Parameter
        ---------
        time_slice:int 
                   The timeslice should be a positive value greater than or equal to zero

    	Examples:
    	-------
    	>>> from pgmpy.models import DynamicBayesianNetwork as DBN
    	>>> dbn = DBN()
    	>>> dbn.add_nodes_from(['D', 'G', 'I', 'S', 'L'])
    	>>> dbn.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('G',0),('L',0)),(('D',0),('D',1))])
    	>>> dbn.get_slice_nodes()
    	"""
    	if not isinstance(time_slice, int) or time_slice < 0:
            raise ValueError("The timeslice should be a positive value greater than or equal to zero")

    	return [(node, time_slice) for node in self.nodes()]

    def add_cpds(self, *cpds):
        """
        This method adds the cpds to the dynamic bayesian network.
        Note that while adding variables and the evidence in cpd,
        they have to be of the following form
        (node_name, time_slice)
        Here, node_name is the node that is inserted
        while the time_slice is an integer value, which denotes
        the index of the time_slice that the node belongs to.

        Parameter
        ---------
        cpds  :  list, set, tuple (array-like)
            List of cpds (TabularCPD, TreeCPD, RuleCPD, Factor)
            which will be associated with the model

        Examples:
        -------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> from pgmpy.factors import TabularCPD
        >>> dbn = DBN()
        >>> dbn.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('D',0),('D',1)),(('I',0),('I',1))])
        >>> grade_cpd = TabularCPD(('G',0), 3, [[0.3,0.05,0.9,0.5],
        ...                                     [0.4,0.25,0.8,0.03],
        ...                                     [0.3,0.7,0.02,0.2]], [('I', 0),('D', 0)],[2,2])
        >>> d_i_cpd = TabularCPD(('D',1),2,[[0.6,0.3],[0.4,0.7]],[('D',0)],2)
        >>> diff_cpd = TabularCPD(('D',0),2,[[0.6,0.4]])
        >>> intel_cpd = TabularCPD(('I',0),2,[[0.7,0.3]])
        >>> i_i_cpd = TabularCPD(('I',1),2,[[0.5,0.4],[0.5,0.6]],[('I',0)],2)
        >>> dbn.add_cpds(grade_cpd, d_i_cpd, diff_cpd, intel_cpd, i_i_cpd)
        >>> dbn.cpds
        """
        for cpd in cpds:
            if not isinstance(cpd, (TabularCPD, TreeCPD, RuleCPD)):
                raise ValueError('cpds should be an instances of TabularCPD, TreeCPD or RuleCPD')

            if set(cpd.variables) - set(cpd.variables).intersection(set(super().nodes())):
                raise ValueError('CPD defined on variable not in the model', cpd)

            self.cpds.append(cpd)

    def get_cpds(self, node=None, time_slice=0):
        """
        Returns the cpds that have been added till now to the graph

        Parameter
        ---------
        node: The node should be be of the following form
        (node_name, time_slice)
        Here, node_name is the node that is inserted
        while the time_slice is an integer value, which denotes
        the index of the time_slice that the node belongs to.

        time_slice:int 
                   The timeslice should be a positive value greater than or equal to zero

        Examples:
        -------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> from pgmpy.factors import TabularCPD
        >>> dbn = DBN()
        >>> dbn.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('D',0),('D',1)),(('I',0),('I',1))])
        >>> grade_cpd =  TabularCPD(('G',0), 3, [[0.3,0.05,0.9,0.5],
        ...                                      [0.4,0.25,0.8,0.03],
        ...                                      [0.3,0.7,0.02,0.2]], [('I', 0),('D', 0)],[2,2])
        >>> dbn.add_cpds(grade_cpd)
        >>> dbn.get_cpds()
        """
        if node:
            if node not in super().nodes():
                raise ValueError('Node not present in the model.')
            else:
                for cpd in self.cpds:
                    if cpd.variable == node:
                        return cpd
        else:
            return [cpd for cpd in self.cpds if set(list(cpd.variables)).issubset(self.get_slice_nodes(time_slice))]

    def check_model(self):
        """
        Check the model for various errors. This method checks for the following
        errors.

        * Checks if the sum of the probabilities for each state is equal to 1 (tol=0.01).
        * Checks if the CPDs associated with nodes are consistent with their parents.

        Returns
        -------
        check: boolean
        True if all the checks are passed
        """
        for node in super().nodes():
            cpd = self.get_cpds(node=node)
            if isinstance(cpd, TabularCPD):
                evidence = cpd.evidence
                parents = self.get_parents(node)
                if set(evidence if evidence else []) != set(parents if parents else []):
                    raise ValueError("CPD associated with %s doesn't have "
                                     "proper parents associated with it." % node)
                if not np.allclose(cpd.marginalize(node, inplace=False).values,
                                   np.ones(np.product(cpd.evidence_card)),
                                   atol=0.01):
                    raise ValueError('Sum of probabilities of states for node {node}'
                                     ' is not equal to 1'.format(node=node))
        return True

    def initialize_initial_state(self):
        """
        This method will automatically re-adjust the cpds and the edges added to the bayesian network.
        If an edge that is added as an intra time slice edge in the 0th timeslice, this method will
        automatically add it in the 1st timeslice. It will also add the cpds. However, to call this
        method, one needs to add cpds as well as the edges in the bayesian network of the whole
        skeleton including the 0th and the 1st timeslice,.

        Examples:
        -------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> from pgmpy.factors import TabularCPD
        >>> student = DBN()
        >>> student.add_nodes_from(['D','G','I','S','L'])
        >>> student.add_edges_from([(('D',0),('G',0)),(('I',0),('G',0)),(('D',0),('D',1)),(('I',0),('I',1))])
        >>> grade_cpd = TabularCPD(('G',0), 3, [[0.3,0.05,0.9,0.5],
        ...                                                 [0.4,0.25,0.8,0.03],
        ...                                                 [0.3,0.7,0.02,0.2]], [('I', 0),('D', 0)],[2,2])
        >>> d_i_cpd = TabularCPD(('D',1),2,[[0.6,0.3],[0.4,0.7]],[('D',0)],2)
        >>> diff_cpd = TabularCPD(('D',0),2,[[0.6,0.4]])
        >>> intel_cpd = TabularCPD(('I',0),2,[[0.7,0.3]])
        >>> i_i_cpd = TabularCPD(('I',1),2,[[0.5,0.4],[0.5,0.6]],[('I',0)],2)
        >>> student.add_cpds(grade_cpd, d_i_cpd, diff_cpd, intel_cpd, i_i_cpd)
        >>> student.initialize_initial_state()
        """
        for cpd in self.cpds:
            temp_var = (cpd.variable[0], 1 - cpd.variable[1])
            parents = self.get_parents(temp_var)
            if not any(x.variable == temp_var for x in self.cpds):
                if all(x[1] == parents[0][1] for x in parents):
                    if parents:
                        new_cpd = TabularCPD(temp_var, cpd.variable_card, np.split(cpd.values, cpd.variable_card), parents,
                           cpd.evidence_card)
                    else:
                        new_cpd = TabularCPD(temp_var, cpd.variable_card, np.split(cpd.values, cpd.variable_card))
                    self.add_cpds(new_cpd)
            self.check_model()

    def moralize(self):
        """
        Removes all the immoralities in the Network and creates a moral
        graph (UndirectedGraph).

        A v-structure X->Z<-Y is an immorality if there is no directed edge
        between X and Y.

        Examples
        --------
        >>> from pgmpy.models import DynamicBayesianNetwork as DBN
        >>> dbn = DBN([(('D',0), ('G',0)), (('I',0), ('G',0))])
        >>> moral_graph = dbn.moralize()
        >>> moral_graph.edges()
        [(('G', 0), ('I', 0)),
        (('G', 0), ('D', 0)),
        (('D', 1), ('I', 1)),
        (('D', 1), ('G', 1)),
        (('I', 0), ('D', 0)),
        (('G', 1), ('I', 1))]
        """
        moral_graph = UndirectedGraph(self.to_undirected().edges())

        for node in super().nodes():
            moral_graph.add_edges_from(itertools.combinations(
                self.get_parents(node), 2))

        return moral_graph
