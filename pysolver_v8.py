# V1 only for river street, rake free
# player 0 = OOP, 1 = IP

# inputs (given in a textfile with each on a new line)
# 1 - pot size
# 2 - stack size
# 3 - OOP range   (eg AsAc, Ac2d:0.2,...)
# 4 - IP range
# 5 - board    (eg JhJs8s5h2d)
# 6 - OOP bet size options (comma separated values as a pct pot or a for all-in)
# 7 - IP bet size options
# 8 - OOP raise size options
# 9 - IP raise size options
# 10 - force All-In threshold (when a bet is greater than this % of the remaining stack that bet is replaced with all-in)
# 11 - max num iterations
# 12 - target exploitability (in pct of the pot)

# output
# json file of strat for each hand in range for each node


ID = -1

from treys import Card, Evaluator
from collections import deque
import json, time
import matplotlib.pyplot as plt


def evalHS(evaluator, hand, board):
    return evaluator.evaluate(board, hand)

def get_inputs(filename):
    '''Returns potsz, stacksz, OOP_range(as dict), IP_range, board, OOP_b_szs, IP_b_szs, OOP_r_szs, IP_r_szs, AI_thresh, max_iters, target_expl'''
    with open(filename, 'r') as file:
        lines = [line.strip() for line in file]

    # Normalize board lines (5 to 8) by replacing 'A' with 'a'
    for i in range(5, 9):
        lines[i] = lines[i].replace('A', 'a')

    def parse_range(line):
        hands = []
        for combo in line.split(','):
            stripped = combo.strip().replace('\t', '')
            if ':' in stripped:
                hand_str, weight = stripped.split(':')
                hands.append(Hand(hand_str, float(weight)))
            else:
                hands.append(Hand(stripped))
        return hands

    OOP_range = parse_range(lines[2])
    IP_range = parse_range(lines[3])

    def split_line(idx):
        return lines[idx].split(',')

    return (
        float(lines[0]),                       # potsz
        float(lines[1]),                       # stacksz
        Range(OOP_range),                      # OOP_range
        Range(IP_range),                       # IP_range
        lines[4],                              # board
        split_line(5),                         # OOP_b_szs
        split_line(6),                         # IP_b_szs
        split_line(7),                         # OOP_r_szs
        split_line(8),                         # IP_r_szs
        float(lines[9]),                       # AI_thresh
        int(lines[10]),                        # max_iters
        float(lines[11])                       # target_expl
    )

    return float(lines[0]), float(lines[1]), Range(OOP_range), Range(IP_range), lines[4], lines[5].split(','), lines[6].split(','), lines[7].split(','), lines[8].split(','), float(lines[9]), int(lines[10]), float(lines[11])

def get_next_ID():
    global ID
    ID += 1
    return ID

def hand_v_range_equity(hand, theRange):
    '''Returns the equity as a decimal of hand against theRange'''
    blockers = {hand.hand[:2], hand.hand[2:]}
    weighting_sum = 0
    equity_tally = 0

    # Precompute hand evaluation
    h_cards = [Card.new(hand.hand[:2]), Card.new(hand.hand[2:])]
    h_eval = evaluator.evaluate(board, h_cards)

    for theHand in theRange.hands_list:
        # Blocker check
        if theHand.hand[:2] in blockers or theHand.hand[2:] in blockers:
            continue

        weight = theHand.weighting * theHand.reach_probability
        weighting_sum += weight

        r_eval = evaluator.evaluate(board, [Card.new(theHand.hand[:2]), Card.new(theHand.hand[2:])])

        if r_eval > h_eval:
            equity_tally += weight
        elif r_eval == h_eval:
            equity_tally += weight / 2

    if weighting_sum == 0:
        return 0.5
    return equity_tally / weighting_sum
        

def update_strat_on_iteration(action_freqs, action_EVs, cummulative_regrets, countfReached): 
    '''Returns new action_freqs, new cumulative regrets'''
    
    expected_utility = sum(f * ev for f, ev in zip(action_freqs, action_EVs))
    
    new_cumm_regs = []
    pos_regrets = []
    sum_of_pos_regrets = 0.0
    
    for ev, reg in zip(action_EVs, cummulative_regrets):
        regret = ev - expected_utility
        updated_regret = reg + regret * countfReached
        new_cumm_regs.append(updated_regret)
        
        pos_regret = max(updated_regret, 0)
        pos_regrets.append(pos_regret)
        sum_of_pos_regrets += pos_regret

    n_actions = len(action_freqs)
    
    if sum_of_pos_regrets <= 0:
        new_strat = [1.0 / n_actions] * n_actions
    else:
        new_strat = [r / sum_of_pos_regrets for r in pos_regrets]

    return new_strat, new_cumm_regs
    

class Tree(object):
    '''A game tree, which contains nodes'''
    def __init__(self, starting_pot, starting_stack, OOP_range, IP_range):
        self.nodes = []
        self.starting_pot = starting_pot
        self.starting_stack = starting_stack
        self.OOP_start_range = OOP_range
        self.IP_start_range = IP_range

    def buildTree(self):
        # to create all nodes, starting from the root:
        # for every available action create a node
        # for each created node create more nodes based on avail actions, if not an endnode

        queue = deque()
        
        root = Node(0, self.OOP_start_range, [], None, self.starting_pot, self.starting_stack, self.starting_stack)
        self.nodes.append(root)
        queue.append(root)
        
        # BFS expansion
        while queue:
            current_node = queue.popleft()
            available_actions = current_node.availActs

            if available_actions == None:
                continue
            
            for action in available_actions:
                # work out the variables for the child node
                # initially don't change weightings for new nodes as strategies not yet initialised
                if current_node.to_act == 0:
                    next_range = self.IP_start_range.getCopy()
                else:
                    next_range = self.OOP_start_range.getCopy()

                # work out new pot size and new IP & OOP stack sizes
                if action in ('X', 'F'):
                    new_ps = current_node.pot_size
                    new_OOP_stack, new_IP_stack = current_node.OOP_stack_size, current_node.IP_stack_size
                    
                elif action == 'C':
                    new_ps = abs(current_node.OOP_stack_size-current_node.IP_stack_size)+ current_node.pot_size
                    new_OOP_stack = new_IP_stack = min(current_node.OOP_stack_size, current_node.IP_stack_size)
                    
                elif action[0] == 'B':
                    if not action[1] == 'A':
                        bet_made = (float(action[1:]) / 100 * current_node.pot_size)
                    else:
                        bet_made = current_node.OOP_stack_size
                    new_ps = current_node.pot_size + bet_made
                    
                    if current_node.to_act == 0:
                        new_OOP_stack = current_node.OOP_stack_size - bet_made
                        new_IP_stack = current_node.IP_stack_size
                    else:
                        new_IP_stack = current_node.IP_stack_size - bet_made
                        new_OOP_stack = current_node.OOP_stack_size
                

                elif action[0] == 'R':
                    if not action[1] == 'A':
                        raise_amnt = (current_node.pot_size + abs(current_node.OOP_stack_size-current_node.IP_stack_size)) * float(action[1:])/100 # note this doesnt include the chips to "call" the last bet or raise before raising
                        
                    else:
                        raise_amnt = max(current_node.OOP_stack_size,current_node.IP_stack_size) - abs(current_node.OOP_stack_size-current_node.IP_stack_size)

                    new_ps = current_node.pot_size + abs(current_node.OOP_stack_size-current_node.IP_stack_size) + raise_amnt

                    if current_node.to_act:
                        new_OOP_stack = current_node.OOP_stack_size
                        new_IP_stack = current_node.OOP_stack_size - raise_amnt
                    else:
                        new_IP_stack = current_node.IP_stack_size
                        new_OOP_stack = current_node.IP_stack_size - raise_amnt
                    
                
                new_node = Node(1 - current_node.to_act, next_range, current_node.action_seq.copy()+[action], current_node, new_ps, new_OOP_stack, new_IP_stack)
                current_node.child_nodes[action] = new_node
                
                self.nodes.append(new_node)
                queue.append(new_node)  # Continue expansion


    def update_reach_probs(self):
        '''Updates reach probabilities for all hands in all child nodes systematically'''
        
        for node in self.nodes:
            if not node.availActs:
                continue

            avail_acts = node.availActs  # Cache the list
            num_actions = len(avail_acts)

            for hand in node.player_range.hands_list:
                handName = hand.hand
                hand_reach_prob = hand.reach_probability
                actions_taken = hand.actions_taken  # Cache the list

                for action_index, action in enumerate(avail_acts):
                    # Instead of index lookup, use enumerate to get the action index directly
                    if action_index >= len(actions_taken):
                        continue  # Safety check

                    action_prob = actions_taken[action_index]
                    reach_prob = hand_reach_prob * action_prob

                    child = node.child_nodes[action]
                    for node_to_update in child.child_nodes.values():
                        hand_to_update = node_to_update.player_range.getHand(handName)
                        hand_to_update.reach_probability = reach_prob

            

    def do_cfr(self, max_iter, target_expl, json_filename):
        '''Does CFR solve and saves to a json file'''
        # algorithm
        # loop until reach either max_iters or target exploitability
        # within loop:
        # first call update_reach_probs
        # then calc EVs for each hand in each node, using reach probs
        # then call update_strat_on_iteration
        # then if every 5th iter, calc exploitability (EV OOP MAX-EXPL-STRAT + EV IP MAX-EXPL-STRAT) - TODO
        # then save into json file
        #

        self.update_reach_probs()

        for i in range(max_iter):
            print(f'{i} / {max_iter}')
            time.sleep(8)
            
            # calc EVs for every hand in every node
            for node in self.nodes:
                node.player_range.calc_EVs(node)

            for node in self.nodes:
                if not node.endNode:
                    reachedFreq = node.getCounterfactReachProb()
                    for hand in node.player_range.hands_list:
                        new_strat, new_cumm_regs = update_strat_on_iteration(hand.avg_strat, hand.EVs, hand.cumm_regrets, reachedFreq)
                        hand.next_strat = new_strat
                        hand.cumm_regrets = new_cumm_regs
                        hand.add_strat_to_avg_strat(new_strat, i+1)

            # now update the strategies to the next calculated one
            for node in self.nodes:
                for hand in node.player_range.hands_list:
                    hand.actions_taken = hand.next_strat

            self.update_reach_probs()
            

            # to add: every 5 iterations calc exploitability and if < target exploitability stop the solver
        
        # set strat to avg_strat
        for node in self.nodes:
            for hand in node.player_range.hands_list:
                hand.actions_taken = hand.avg_strat
        self.update_reach_probs()

        nodes = []
        for node in self.nodes:
            rg_strat = {}
            rg_EVs = {}
            act_EVs = {}
            for hand in node.player_range.hands_list:
                rg_strat[hand.hand] = hand.avg_strat
                rg_EVs[hand.hand] = node.calc_EV_hand(hand, node.to_act)
                act_EVs[hand.hand] = node.calc_EV_hand_all_acts(hand, node.to_act)
            nodes.append({'id':node.ID, 'atn-sq':node.action_seq, 'avl-acs':node.availActs, 'rg-strat':rg_strat, 'act-EVs':act_EVs, 'rg-EVs':rg_EVs})
            
        
        with open(json_filename, 'w') as json_file:
            json.dump(nodes, json_file, indent=4)

        

class Node(object):
    '''One node of the tree'''
    def __init__(self, to_act, player_range, action_seq, parent_node, pot_size, OOP_stack_size, IP_stack_size):
        self.ID = get_next_ID()
        self.to_act = to_act
        self.player_range = player_range
        self.pot_size = pot_size
        self.OOP_stack_size = OOP_stack_size
        self.IP_stack_size = IP_stack_size
        self.child_nodes = {} # a dict of action_taken:node
        
        self.action_seq = action_seq # tuple or list of previous actions eg F, B50, R33
        self.parent_node = parent_node
        self.isLocked = False # to be used when nodelocking added
        self.endNode = False
        self.getAvailActions()
        if self.availActs:
            self.player_range.initialize_strats(len(self.availActs))

    def __str__(self):
        return f'---------------\n\nID:\t{self.ID}\nto_act:\t{self.to_act}\npot_size:\t{self.pot_size}\nOOP_stack_size:\t{self.OOP_stack_size}\nIP_stack_size:\t{self.IP_stack_size}\n\
action_seq:\t{self.action_seq}\nendNode\t{self.endNode}\navailActs:\t{self.availActs}\nplayer_range:\t{str(self.player_range)}'
    
    def getHeroStackSize(self):
        if self.hero:
            return self.IP_stack_size
        return self.OOP_stack_size

    def updateRange(self, new_range):
        self.player_range = player_range

    def getAvailActions(self):
        # if root node or node after a 'X' action
        if not self.action_seq:
            self.availActs = ['X']
            for size in OOP_b_szs:
                if 'a' in size.lower():
                    if not 'BA' in self.availActs:
                        self.availActs.append('BA')
                else:
                    if float(size)/100 * self.pot_size > self.IP_stack_size * AI_thresh/100:
                        if not ('BA' in self.availActs):
                            self.availActs.append('BA')
                    else:
                        self.availActs.append(f'B{size}')
        elif self.action_seq[-1] == 'X':
            if self.action_seq and self.parent_node.to_act == 1: # IP last acted, hand is over
                self.endNode = True
                self.availActs = None
            else:
                self.availActs = ['X']
                for size in IP_b_szs:
                    if 'a' in size.lower():
                        if not 'BA' in self.availActs:
                            self.availActs.append('BA')
                    else:
                        if float(size)/100 * self.pot_size > self.IP_stack_size * AI_thresh/100:
                            if not ('BA' in self.availActs):
                                self.availActs.append('BA')
                        else:
                            self.availActs.append(f'B{size}')

        elif self.action_seq[-1] in ('F', 'C'):
            self.endNode = True
            self.availActs = None

        elif self.action_seq[-1][0] == 'B':
            self.availActs = ['F', 'C']
            if self.action_seq[-1][1] == 'A':
                return
            bet_size = float(self.action_seq[-1][1:])
            pot_before_bet = self.parent_node.pot_size
            if self.to_act == 0:
                r_sizes = OOP_r_szs
            else:
                r_sizes = IP_r_szs
            
            for size in r_sizes:
                if 'a' in size.lower():
                    if not 'RA' in self.availActs:
                        self.availActs.append('RA')
                else:
                    if ((pot_before_bet + 2*bet_size*pot_before_bet/100) * float(size)/100 + bet_size/100 * pot_before_bet) > AI_thresh/100 * (self.OOP_stack_size if not self.to_act else self.IP_stack_size):
                        if not 'RA' in self.availActs:
                            self.availActs.append('RA')
                    else:
                        self.availActs.append(f'R{size}')

        elif self.action_seq[-1][0] == 'R':
            self.availActs = ['F', 'C']
            if self.action_seq[-1][1] == 'A':
                return

            raise_size = self.action_seq[-1][1:]

            # first traverse back through nodes until find one after which initial bet was made
            node = self.parent_node
            while node.action_seq[-1][0] != 'B':
                node = node.parent_node
            node = node.parent_node

            if self.to_act:
                pot_size_if_r_called = (node.OOP_stack_size - self.OOP_stack_size) * 2 + node.pot_size
                if ((node.OOP_stack_size - self.OOP_stack_size) + pot_size_if_r_called * float(raise_size)/100) > node.IP_stack_size * AI_thresh/100:
                    if not 'RA' in self.availActs:
                        self.availActs.append('RA')
                else:
                    self.availActs.append(f'R{raise_size}')

            else:
                pot_size_if_r_called = (node.IP_stack_size - self.IP_stack_size) * 2 + node.pot_size
                if ((node.IP_stack_size - self.IP_stack_size) + pot_size_if_r_called * float(raise_size)/100) > node.OOP_stack_size * AI_thresh/100:
                    if not 'RA' in self.availActs:
                        self.availActs.append('RA')
                else:
                    self.availActs.append(f'R{raise_size}')

    def getCounterfactReachProb(self):
        '''Returns the probability this node was reached from the root if the hero player at this node always tried to get there'''
        analysedNode = self
        probability = 1
        while analysedNode.parent_node:
            parNode = analysedNode.parent_node
            if parNode.to_act == self.to_act:
                # don't need this to affect the probability
                analysedNode = parNode
                continue
            
            range_freqs = parNode.player_range.get_range_action_freqs()

            # find the action just taken
            probability *= range_freqs[parNode.availActs.index(analysedNode.action_seq[-1])]
            analysedNode = parNode

        return probability

    def calc_EV_hand_and_action(self, theHand, action, hero):
        '''calcs the EV of theHand from this node of taking this action'''
        EV = 0
        # takes action -> next node
        # EV = weighted sum of actions taken * EV for hero once get to node after action taken
        # along the way if put money in need to +/- this from EV
        # once reach an end node, if was a fold EV is either 0 or pot depending on who folded
        # if was a X or C, EV is based on EQ vs villains range * pot

        if self.endNode:
            if self.action_seq[-1] in ('X', 'C'):
                if self.to_act == hero:
                    vilsRange = self.parent_node.player_range.getCopy()
                    # need to multiply RPs of hands in this range by freq they took the act just taken
                    for hand in vilsRange.hands_list:
                        freq_took_last_action = self.parent_node.player_range.getHand(hand.hand).actions_taken[self.parent_node.availActs.index(self.action_seq[-1])]
                        hand.reach_probability *= freq_took_last_action
                else:
                    vilsRange = self.player_range # ensure RPs have been updated after any strat (actions_taken) change, before running this
                EV += hand_v_range_equity(theHand, vilsRange) * self.pot_size

            elif self.action_seq[-1] == 'F':
                if self.to_act == hero: # villain just folded
                    EV += self.pot_size
                
        else:

            if hero == self.to_act: # a hero node so need to include the action EV
                if hero == 0:
                    act_EV = self.child_nodes[action].OOP_stack_size - self.OOP_stack_size
                else:
                    act_EV = self.child_nodes[action].IP_stack_size - self.IP_stack_size
                    
                EV += act_EV
            
            EV += self.child_nodes[action].calc_EV_hand(theHand, hero)

        return EV

    def calc_EV_hand(self, theHand, hero):
        '''calcs the EV of theHand with its current mixed strategy'''
        EV = 0
        if self.endNode:
            EV += self.calc_EV_hand_and_action(theHand, None, hero)
        else:
            if self.to_act == hero:
                hero_hand_on_this_node = self.player_range.getHand(theHand.hand)
            else:
                vil_action_freqs = self.player_range.get_range_action_freqs()
            for i in range(len(self.availActs)):
                # if a hero node need to lookup the original hand for the current range to see freqs of each action
                if self.to_act == hero:
                    EV += hero_hand_on_this_node.actions_taken[i] * self.calc_EV_hand_and_action(theHand, self.availActs[i], hero)
                else:
                    EV += vil_action_freqs[i] * self.calc_EV_hand_and_action(theHand, self.availActs[i], hero)
        return EV

    def calc_EV_hand_all_acts(self, theHand, hero):
        '''Returns a list of EVs of all possible actions in order'''
        ls = []
        if self.endNode:
            # list is just one element of that EV
            ls.append(self.calc_EV_hand_and_action(theHand, None, hero))
            
        else:
            for act in self.availActs:
                ls.append(self.calc_EV_hand_and_action(theHand, act, hero))
        
        return ls

    def calc_EV_range(self):
        '''calcs the EV of the players range from this node with its current strategy'''
        EV = 0
        cur_node = self.parent_node
        prev_node = self
        while cur_node != None:
            prev_node = cur_node
            cur_node = cur_node.parent_node

        if cur_node.to_act == self.to_act:
            init_weight_range = cur_node.player_range
        else:
            init_weight_range = prev_node.player_range
        
        for hand in self.player_range.hands_list:
            EV += init_weight_range.getHand(hand.hand).weighting * hand.reach_probability * self.calc_EV_hand(hand, self.to_act)

        return EV



class Hand(object):
    '''Represents a hand, lists of which are a range'''
    def __init__(self, hand, weighting=1, actions_taken=[], cumm_regrets=[]):
        '''hand parameter is eg AsKc, actions_taken is eg [0, 0.4, 0.6]'''
        self.hand = hand
        self.weighting = weighting
        self.actions_taken = actions_taken
        self.cumm_regrets = cumm_regrets
        self.reach_probability = 1
        self.EVs = []
        self.avg_strat = actions_taken
        self.next_strat = []

    def add_strat_to_avg_strat(self, thisStrat, iter_num):
        '''iter_num should be 1 for the first iteration'''
        for i in range(len(self.avg_strat)):
            self.avg_strat[i] = self.avg_strat[i] * (iter_num-1)/iter_num + thisStrat[i] * 1/iter_num
        

class Range(object):
    def __init__(self, hands_list):
        self.hands_list = hands_list

    def __str__(self):
        stng = ''
        for hand in self.hands_list:
            stng += f'\n{hand.hand}:\t{hand.weighting}\nactions_taken:\t{hand.actions_taken}\ncumm regs:\t{hand.cumm_regrets}\nreach prob:\t{hand.reach_probability}\nEVs:\t{hand.EVs}\navg_strat:\t{hand.avg_strat}\n\n'
        return stng

    def getHand(self, hand_name):
        '''Returns the hand object from its string name'''
        for hand in self.hands_list:
            if hand.hand == hand_name:
                return hand
        return None

    def getCopy(self):
        new_range_hands = []
        for hand in self.hands_list:
            new_range_hands.append(Hand(hand.hand, hand.weighting))
        return Range(new_range_hands)

    def initialize_strats(self, num_poss_acts):
        '''inits strats, cumm_regrets. For every hand in range gives an equal proportion to each possible action'''
        if not num_poss_acts:
            return
        for hand in self.hands_list:
            hand.actions_taken = [round(1/num_poss_acts,3)] * num_poss_acts
            hand.cumm_regrets = [0] * num_poss_acts
            hand.avg_strat = [round(1/num_poss_acts,3)] * num_poss_acts

    def calc_EVs(self, node):
        for hand in self.hands_list:
            hand.EVs = node.calc_EV_hand_all_acts(hand, node.to_act)

    def get_range_action_freqs(self):
        '''Returns the list of action freqs of the entire range'''
        num_acts = len(self.hands_list[0].actions_taken)
        frqs = [0] * num_acts
        total_weight = 0
        for hand in self.hands_list:
            for i in range(num_acts):
                frqs[i] += hand.weighting * hand.reach_probability * hand.actions_taken[i]

        sum_frqs = sum(frqs)

        if sum_frqs == 0: # may need to change this in future?
            return [0]*len(frqs)
        
        for i in range(len(frqs)):
            frqs[i] = frqs[i]/sum_frqs

        return frqs
        


def main(inputs_file_name, outputs_file_name):
    global OOP_b_szs, IP_b_szs, OOP_r_szs, IP_r_szs, AI_thresh, evaluator, board
    evaluator = Evaluator()
    potsz, stacksz, OOP_range, IP_range, board, OOP_b_szs, IP_b_szs, OOP_r_szs, IP_r_szs, AI_thresh, max_iters, target_expl = get_inputs(inputs_file_name)
    if OOP_b_szs==['']: OOP_b_szs=[]
    if IP_b_szs==['']: IP_b_szs=[]
    if OOP_r_szs==['']: OOP_r_szs=[]
    if IP_r_szs==['']: IP_r_szs=[]
    tree = Tree(potsz, stacksz, OOP_range, IP_range)
    board = (board[:2], board[2:4], board[4:6], board[6:8], board[8:10])
    board = [Card.new(card) for card in board]
    tree.buildTree()
    tree.do_cfr(max_iters, target_expl, outputs_file_name)


if __name__ == "__main__":
    main('solver_inputs.txt', 'solver_results.json')
