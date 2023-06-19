import disnake


class TrashButton(disnake.ui.Button):
    """Creates a Trash button to delete the message it's attached to"""

    def __init__(self, member_id: int):
        super().__init__(
            emoji="🪓",
            style=disnake.ButtonStyle.gray,
            custom_id=f"{member_id}_trash",
        )
