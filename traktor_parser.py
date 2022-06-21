# C:\Users\Nono\Documents\Native Instruments\Traktor 3.0.0

# from traktor_nml_utils import TraktorCollection

# collection = TraktorCollection(path='collection.nml')

# for entry in collection.nml.entry:
#     print(entry.artist, entry.title, entry.info.ranking)
import xml.etree.ElementTree as ET

class TraktorBoxParser:
    def __init__(self,path,verbose=True):
        self.tree = ET.parse(path)
    


if __name__ == "__main__":

    node = ET.Element("NODE")
    node.set("TYPE", "PLAYLIST")
    node.set("NAME", "PLAYLIST_TEST")
    playlist = ET.SubElement(node, "PLAYLIST")
    playlist.set("ENTRIES", "ENTRIES_TEST")
    playlist.set("TYPE", "LIST")
    playlist.set("UUID", "UUID_TEST")
    track_entry = ET.SubElement(playlist, "ENTRY")
    track_primary_key = ET.SubElement(track_entry, "PRIMARY_KEY")
    track_primary_key.set("TYPE", "TRACK")
    track_primary_key.set("KEY", "KEY_TEST")
    ET.dump(node)

    tree = ET.parse("collection.nml")
    root = tree.getroot()
    for child in root:
        if child.tag == "PLAYLISTS":
            for node in child:
                for subnodes in node:
                    print(subnodes)
                    # subnodes.insert(1,node)
                    subnodes.append(node)
                    for playlist in subnodes:
                        print(playlist.attrib)
