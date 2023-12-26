class InvalidClient(Exception):
    """Signal for when the voice channel attempting to connect is null"""
    pass


class JoinError(Exception):
    """Signal for when the Bot couldn't join the channel"""
    pass
