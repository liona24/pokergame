import threading
from collections import namedtuple, defaultdict
from functools import reduce

import deuces

RoundSummary = namedtuple('RoundSummary',
                          'hands_played board players winners blinds')

evaluator = deuces.Evaluator()


def distribute_pot(players, board):

    players = set(players)
    active_players = list(filter(lambda x: not x.has_folded, players))
    scores = defaultdict(list)

    if not board:
        assert len(active_players) == 1

    if len(active_players) == 1:
        scores[0].append(active_players[0])
    else:
        for p in active_players:
            p.hand_score = evaluator.evaluate(p.hand, board)
            scores[p.hand_score].append(p)

    rv = []

    for score in sorted(scores):
        winners = filter(lambda x: x.bet > 0, scores[score])
        winners = sorted(winners, key=lambda x: x.bet)
        pot = 0
        for n, winner in enumerate(winners):
            to_remove = set()
            winner_bet = winner.bet  # read only copy
            for p in players:
                share = min(p.bet, winner_bet)
                p.bet -= share
                if p.bet == 0:
                    to_remove.add(p)
                pot += share

            players -= to_remove

            winners_share = pot // (len(winners) - n)
            winner.stack += winners_share
            rv.append((winner, winners_share))
            pot -= winners_share

        if not len(players):
            break

    return rv


def bet_round(first_player_idx, players, board, bet, n_left):

    i = first_player_idx
    raised = first_player_idx
    is_first_round = True

    while n_left > 1:
        if not is_first_round and raised == i:
            break

        is_first_round = False

        p = players[i]
        if not p.is_allin and not p.has_folded:
            to_call = bet - p.bet
            betsize = p.move(players, board, to_call)

            if betsize < 0:  # fold
                p.hand = []
                p.has_folded = True
                n_left -= 1
            else:
                assert betsize <= p.stack, 'Player betted more than available!'

                if betsize < to_call:
                    betsize = min(p.stack, to_call)

                p.bet += betsize
                p.stack -= betsize

                if betsize > to_call:
                    raised = i
                    bet += betsize - to_call

        i = (i + 1) % len(players)

    return bet, n_left


class Game(object):

    def __init__(self, players, blinds,
                 blindstep=lambda hands, blinds: blinds):

        self.players = players

        self.blinds = blinds
        self.blindstep = blindstep
        self.hands_played = 0

        self.big_blind = 0

    @property
    def num_players(self):
        return len(self.players)

    def join(self, player, position):
        """Add a player to this game

        TODO: This method is NOT thread safe

        Arguments:
            player {player.BasePlayer} -- The player to be added
            position {int} -- The position at the 'table' to insert the player
        """
        self.players.insert(position, player)

    def leave(self, player):
        """Remove a player from this game

        TODO: This method is NOT thread safe

        Arguments:
            player {player.BasePlayer} -- The player to be removed.
        """
        self.players.remove(player)

    def play(self, dealt_hook=None, flop_hook=None, turn_hook=None,
             river_hook=None, winner_hook=None):
        """Generator to yield hand summaries after playing rounds of poker.

        All hooks are of signature func(the_game_instance) -> None

        Keyword Arguments:
            dealt_hook {callable} -- A function called after hands are dealt
                and blinds are placed. (default: {None})
            flop_hook {callable} -- A function called after the flop cards were
                dealt but before players bet (default: {None})
            turn_hook {callable} -- A function called after the turn card was
                dealt but before players bet (default: {None})
            river_hook {callable} -- A function called after the river card was
                dealt but before players bet (default: {None})
            winner_hook {callable} -- A function called after the winner is
                determined (default: {None})
        """

        while True:
            if len(self.players) == 1:
                return

            # big blind always position 1
            # small blind always position 0
            deck = deuces.Deck()
            board = []

            # create copy of players for this round
            # this allows adding playing while a round is in progress
            players = self.players[:]

            for player in players:
                player.reset(deck.draw(2))

            blind_positions = [
                (self.big_blind - 1) % len(players),
                self.big_blind
            ]

            for b, bi in zip(self.blinds, blind_positions):
                p = players[bi]
                assert p.stack > 0
                p.bet = min(p.stack, b)
                p.stack -= p.bet

            bet = max([ players[i].bet for i in blind_positions ])

            if dealt_hook is not None:
                dealt_hook(self)

            rounds = [ (blind_positions[1] + 1) % len(players) ] +\
                [ blind_positions[0] ] * 3
            n_dealt = [ 3, 1, 1, 0 ]  # note the last is dummy
            hooks = [ flop_hook, turn_hook, river_hook, None ]

            n_left = reduce(lambda x, y: x + int(not y.has_folded),
                            players,
                            0)

            for i, hook, n_dealt in zip(rounds, hooks, n_dealt):

                bet, n_left = bet_round(i, players, board, bet, n_left)

                if n_left == 1:
                    break

                board.extend(deck.draw(n_dealt))
                if hook is not None:
                    hook(self)

            winners = distribute_pot(players, board)
            players = list(filter(lambda p: p.stack > 0, players))

            yield RoundSummary(self.hands_played,
                               board,
                               players,
                               winners,
                               self.blinds)

            self.big_blind = (self.big_blind + 1) % len(self.players)
            self.hands_played += 1
            self.blinds = self.blindstep(self.hands_played, self.blinds)
            self.players = list(filter(lambda p: p.stack > 0, self.players))

    def play_async(self, game_finished_callback, summary_hook=None,
                   dealt_hook=None, flop_hook=None, turn_hook=None,
                   river_hook=None, winner_hook=None):
        """Wrapper around play(..) to start the game loop in its own thread.

        All hooks are of signature func(the_game_instance) -> None
        (except summary_hook)

        Arguments:
            game_finished_callback {callable} -- A function to be called
                when the game ends (can be ``None``)

        Keyword Arguments:
            summary_hook {callable} -- A function called after each round
                played (func(RoundSummary) -> None). This function can be used
                to process what the generator would have yielded in the single-
                thread case. (default: {None})
            dealt_hook {callable} -- A function called after hands are dealt
                and blinds are placed. (default: {None})
            flop_hook {callable} -- A function called after the flop cards were
                dealt but before players bet (default: {None})
            turn_hook {callable} -- A function called after the turn card was
                dealt but before players bet (default: {None})
            river_hook {callable} -- A function called after the river card was
                dealt but before players bet (default: {None})
            winner_hook {callable} -- A function called after the winner is
                determined (default: {None})

        Returns a function which can be called to request stopping:
            request_stop(blocking=False) -> None
        """
        stop_event = threading.Event()

        def run():
            for summary in self.play(dealt_hook=dealt_hook,
                                     flop_hook=flop_hook,
                                     turn_hook=turn_hook,
                                     river_hook=river_hook,
                                     winner_hook=winner_hook):
                if summary_hook is not None:
                    summary_hook(summary)

                if stop_event.is_set():
                    break

            if game_finished_callback is not None:
                game_finished_callback()

        thread = threading.Thread(target=run, daemon=True)

        def request_stop(blocking=False):
            stop_event.set()
            if blocking:
                thread.join()

        thread.start()

        return request_stop
