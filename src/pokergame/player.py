class PlayerBase(object):
    """The base class for all players.

    The default player is an bot which is always calling.
    """

    def __init__(self, name, initstack):
        self.name = name

        #
        # These properties should be readonly and only altered by the dealer
        #
        # hand  - The players hand cards
        self.hand = []
        # stack - The total chip count the player has
        self.stack = initstack
        # bet   - The amount the player already put in the pot
        self.bet = 0
        # has_folded - Whether the play is still in or not
        self.has_folded = False
        # hand_score - The score of the player's last hand (lower is better)
        self.hand_score = None

    def reset(self, hand):
        self.hand = hand
        self.bet = 0
        self.has_folded = False
        self.hand_score = None

    @property
    def is_allin(self):
        return self.stack == 0

    def move(self, players, board, to_call):
        """Return the betsize:
        If betsize < 0: Fold
        If betsize = to_call: Call
        If betsize > to_call: Raise

        The betsize should always be less than the stack available.

        The default behaviour is always calling.
        """

        if to_call <= self.stack:
            return to_call

        return -1

    def __repr__(self):
        return "Player('%s', stack=%d, bet=%d)" %\
            (self.name, self.stack, self.bet)

    def __str__(self):
        return "Player('%s', stack=%d, bet=%d)" %\
            (self.name, self.stack, self.bet)
