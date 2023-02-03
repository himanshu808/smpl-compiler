from app.custom_types import InstrNodeType, InstrNodeActual
from app.parser.basic_blocks import BB
from app.parser.instr_graph import InstrGraph
from app.parser.instr_node import OpInstrNode, EmptyInstrNode
from app.tokens import OpCodeEnum
from typing import Optional
from app.tokenizer import Tokenizer


class CFG:
    def __init__(self) -> None:
        self.const_bb: Optional[BB] = None
        self._instr_graph: InstrGraph = InstrGraph()
        self.bb_num: int = 0
        self.curr_bb: Optional[BB] = None
        self._predecessors: list[list[int]] = list()
        self._successors: list[list[int]] = list()
        self._dom_predecessors: list[int] = list()
        self._bb_map: list[BB] = list()
        self.declared_vars: set[int] = set()
        self.__initialize_cfg()

    def get_bb(self, bb_num: int) -> BB:
        return self._bb_map[bb_num]

    def update_bb_map(self, bb_obj: BB) -> None:
        self._bb_map.append(bb_obj)

    def update_predecessors(self, bb_num: int, other: list[int]) -> None:
        if len(self._predecessors) == bb_num:
            self._predecessors.append([])
        self._predecessors[bb_num].extend(other)

    def update_successors(self, bb_num: int, other: list[int]) -> None:
        if len(self._successors) == bb_num:
            self._successors.append([])
        self._successors[bb_num].extend(other)

    def update_dom_predecessors(self, bb_num: int, other: list[int]) -> None:
        if len(self._dom_predecessors) == bb_num:
            self._dom_predecessors.append(-1)
        self._dom_predecessors[bb_num] = other[0] if other else -1

    def __initialize_cfg(self) -> None:
        bb0: int = self.create_bb([])
        bb1: int = self.create_bb([bb0], [])
        self.const_bb = self.get_bb(bb0)

    def build_instr_node(self, node_type: InstrNodeType, opcode: OpCodeEnum, bb: Optional[int] = None, **kwargs) -> int:
        if bb is None:
            bb = self.curr_bb
        else:
            bb = self.get_bb(bb)
        instr_num: Optional[int] = bb.get_first_instr_num()
        if instr_num is not None:
            if not isinstance(self._instr_graph.get_instr(instr_num), EmptyInstrNode):
                instr_num = None
            else:
                bb.remove_empty_instr()
        instr_num: int = self._instr_graph.build_instr_node(node_type, opcode, instr_num, **kwargs)
        bb.update_instr_list(instr_num, is_phi=opcode == OpCodeEnum.PHI.value)
        return instr_num

    def get_var_instr_num(self, bb: BB, ident: int, visited_bb: set[int]) -> Optional[int]:
        if bb.bb_num in visited_bb:
            return
        visited_bb.add(bb.bb_num)
        if bb.check_instr_exists(ident):
            return bb.get_var_instr_num(ident)

        search_space: list[int] = self._predecessors[bb.bb_num]
        res: list[int] = list()
        for node in search_space:
            instr = self.get_var_instr_num(self._bb_map[node], ident, visited_bb)
            if instr is not None:
                res.append(instr)

        instr_num: Optional[int] = None
        res: list[int] = list(res)
        if len(res) > 1 and res[0] != res[1]:
            instr_num = self.build_instr_node(OpInstrNode, OpCodeEnum.PHI.value, bb=bb.bb_num, left=res[0],
                                              right=res[1])
        elif len(set(res)) == 1:
            instr_num = res[0]
        elif bb.bb_num == 0:
            print(f"Warning!: {Tokenizer.id2string(ident)} referenced before assignment!")
            instr_num = 0  # uninitialized vars

        return instr_num

    def create_bb(self, predecessors: list[int], dom_predecessors: Optional[list[int]] = None) -> int:
        if dom_predecessors is None:
            dom_predecessors = predecessors

        new_bb: BB = BB(self.bb_num)
        self.curr_bb = new_bb
        self.update_bb_map(self.curr_bb)
        self.update_predecessors(self.bb_num, predecessors)
        self.update_dom_predecessors(self.bb_num, dom_predecessors)
        self.update_successors(self.bb_num, [])
        self.build_instr_node(EmptyInstrNode, OpCodeEnum.EMPTY.value)

        for parent in predecessors:
            self.update_successors(parent, [self.bb_num])

        self.bb_num += 1
        return self.curr_bb.bb_num

    def get_instr(self, instr_num: int) -> InstrNodeActual:
        return self._instr_graph.get_instr(instr_num)

    def update_instr(self, instr_num: int, change_dict: dict[str, int]) -> None:
        instr = self._instr_graph.get_instr(instr_num)
        assert isinstance(instr, OpInstrNode), "can only update OpInstrNode"
        instr.update_instr(change_dict)

    def debug(self) -> None:
        for bb in self._bb_map:
            bb.debug()
        print("\nPredecessors:")
        for bb_num, bb_list in enumerate(self._predecessors):
            print(f"BB{bb_num}: {bb_list}")

        print("\nSuccessors:")
        for bb_num, bb_list in enumerate(self._successors):
            print(f"BB{bb_num}: {bb_list}")

        print("\nDom Predecessors:")
        for bb_num, bb in enumerate(self._dom_predecessors):
            print(f"BB{bb_num}: {bb}")
