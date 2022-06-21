from Parsers import RecordBoxParser, TraktorParser


TRAKTOR_COLLECTION_PATH = (
    "C:\\Users\\Nono\\Documents\\Native Instruments\\Traktor 3.0.0\\collection.nml"
)
RECORDBOX_COLLECTION_PATH = (
    "C:\\Users\\Nono\\AppData\\Roaming\\Pioneer\\rekordbox\\recordbox.xml"
)

# --------------------------------------------
# Copy playlists from Traktor box to Recordbox
# --------------------------------------------

# Get Traktor collection
traktor_parser = TraktorParser(
    TRAKTOR_COLLECTION_PATH,
    verbose=True,
)

# Remove _LOOPS and _RECORDINGS from traktor playlist
traktor_playlists = traktor_parser.playlists[:-2]

# Get Recordbox collection
record_parser = RecordBoxParser(RECORDBOX_COLLECTION_PATH, verbose=True)

# Save traktor playlist to RecordBox collection
record_parser.add_playlists_to_tree(traktor_playlists)

# Save RecordBox Collection
record_parser.save_file(backup=True)

# --------------------------------------------
# Copy playlists from Recordbox to Traktor box
# --------------------------------------------

# # Get Recordbox collection
# record_parser = RecordBoxParser(RECORDBOX_COLLECTION_PATH, verbose=True)

# # Get Traktor collection
# traktor_parser = TraktorParser(
#     TRAKTOR_COLLECTION_PATH,
#     verbose=True,
# )

# # Save RecordBox playlists to Traktor Collection
# traktor_parser.add_playlists_to_tree(record_parser.playlists)

# # Save Traktor Collection
# traktor_parser.save_file(backup=True)
