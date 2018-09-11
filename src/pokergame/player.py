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
        self.hand = None
        # stack - The total chip count the player has
        self.stack = initstack
        # bet   - The amount the player already put in the pot
        self.bet = 0

    @property
    def is_allin(self):
        return self.bet == self.stack

    def move(self, players, board, to_call, pot):
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
