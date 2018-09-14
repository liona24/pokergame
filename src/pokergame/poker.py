import io
import threading

import deuces


def string_printer(string):

    def printer(*args, **kvargs):
        print(*args, **kvargs, file=string)

    return printer


def bet_round(first_player_idx, players, board, pot, bet=0):

    i = first_player_idx
    raised = first_player_idx
    is_first_round = True

    while len(players) > 1:
        if not is_first_round and raised == i:
            break

        is_first_round = False

        p = players[i]
        to_call = bet - p.bet
        betsize = p.move(players, board, to_call, pot)

        if betsize < 0:  # fold
            p.hand = []
            players.remove(p)
            i -= 1
            raised -= 1
        else:
            assert betsize <= p.stack, 'Player betted more than available!'
            assert betsize >= to_call, 'All-In is not implemented!'

            p.bet += betsize
            p.stack -= betsize
            pot += betsize

            if betsize > to_call:
                raised = i
                bet += betsize - to_call

        i = (i + 1) % len(players)

    return pot


class Game(object):

    def __init__(self, players, blinds,
                 blindstep=lambda hands, blinds: blinds):

        self.players = players

        self.blinds = blinds
        self.blindstep = blindstep
        self.hands_played = 0

        self.big_blind = 0

        self.evaluator = deuces.Evaluator()

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

    def _order_players(self):
        """Reorders the players according to current big blind position.
        """

        bb = self.big_blind
        sb = (self.big_blind - 1) % len(self.players)

        lst = self.players
        if bb == 0:
            return [ lst[-1] ] + lst[:-1]
        return [ lst[sb], lst[bb] ] + lst[bb + 1:] + lst[:bb - 1]

    def play(self, dealt_hook=None, flop_hook=None, turn_hook=None,
             river_hook=None, winner_hook=None):
        """Generator to yield hand summaries after playing rounds of poker.

        All hooks are of signature func(list_of_active_players) -> None

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

            output = io.StringIO()
            print_ = string_printer(output)

            print_("Hand #%d\n" % (self.hands_played + 1))

            # big blind always position 1
            # small blind always position 0
            players = self._order_players()
            deck = deuces.Deck()
            board = []

            pot = sum(self.blinds)  # TODO all-in cases
            bet = self.blinds[1]

            for player in players:
                player.hand = deck.draw(2)
                player.bet = 0

            players[0].bet = self.blinds[0]  # small blind
            players[1].bet = self.blinds[1]  # big blind
            players[0].stack -= self.blinds[0]  # small blind
            players[1].stack -= self.blinds[1]  # big blind

            if dealt_hook is not None:
                dealt_hook(players)

            rounds = [ 2 % len(players), 0, 0, 0 ]
            n_dealt = [ 3, 1, 1, 0 ]  # note the last is dummy
            hooks = [ flop_hook, turn_hook, river_hook, None ]

            for i, hook, n_dealt in zip(rounds, hooks, n_dealt):

                pot = bet_round(i, players, board, pot, bet)

                if len(players) == 1:
                    p = players[0]
                    p.stack += pot
                    print_("%s is the winner!" % p.name)
                    break

                board.extend(deck.draw(n_dealt))
                if hook is not None:
                    hook(players)

                for player in players:
                    player.bet = 0
                bet = 0

            if len(players) > 1:
                winners = self.evaluator.hand_summary(board,
                                                      players,
                                                      print=print_)
                splitpot = pot // len(winners)
                for winner in winners:
                    winner.stack += splitpot

            print_("Pot size: %d" % pot)

            self.big_blind = (self.big_blind + 1) % len(self.players)
            self.hands_played += 1
            self.blinds = self.blindstep(self.hands_played, self.blinds)

            summary = output.getvalue()
            output.close()

            yield summary

    def play_async(self, summary_hook=None, dealt_hook=None, flop_hook=None,
                   turn_hook=None, river_hook=None, winner_hook=None):
        """Wrapper around play(..) to start the game loop in its own thread.

        All hooks are of signature func(list_of_active_players) -> None
        (except summary_hook)

        Keyword Arguments:
            summary_hook {callable} -- A function called after each round
                played (func(str) -> None). This function can be used to
                process what the generator would have yielded in the single-
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

        thread = threading.Thread(target=run, daemon=True)

        def request_stop(blocking=False):
            stop_event.set()
            if blocking:
                thread.join()

        thread.start()

        return request_stop
