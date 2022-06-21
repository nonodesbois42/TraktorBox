from abc import abstractmethod
from contextlib import suppress
from enum import Enum
import os
import shutil
from typing import Iterable
import xml.etree.ElementTree as ET
from urllib import parse
import uuid

# Recordbox.xml standard path:
# C:\Users\User_Name\AppData\Roaming\Pioneer\rekordbox

# Collection.nml standard path:
# C:\Users\Nono\Documents\Native Instruments\Traktor 3.0.0


class Debug:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def print(self, *args):
        if self.verbose:
            print(*args)


class Software(Enum):
    TRAKTOR = "Traktor"
    RECORDBOX = "RecordBox"


class Song:
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return self.__str__()

    @classmethod
    def record_path_to_normal_path(csl, record_path: str):
        # from file://localhost/C:/Users/Nono/Music/MIX/02%20-%20HOUSE/CHILL/Time.mp3
        # to  C:\Users\Nono\Music\MIX\02 - HOUSE\CHILL\Time.mp3
        normal_path = parse.unquote(record_path)
        normal_path = normal_path.removeprefix("file://localhost/")
        normal_path = normal_path.replace("/", "\\")
        return normal_path

    @classmethod
    def normal_path_to_traktor_path(self, path: str):
        # from C:\Users\Nono\Music\MIX\03 - DISCO\Deepswing - In The Music (Original Mix).mp3
        # to C:/:Users/:Nono/:Music/:MIX/:03 - DISCO/:Deepswing - In The Music (Original Mix).mp3
        new_path = path.replace("\\", "/:")
        return new_path

    @classmethod
    def traktor_path_to_normal_path(self, traktor_path: str):
        # from C:/:Users/:Nono/:Music/:MIX/:03 - DISCO/:Deepswing - In The Music (Original Mix).mp3
        # to C:\Users\Nono\Music\MIX\03 - DISCO\Deepswing - In The Music (Original Mix).mp3
        normal_path = traktor_path.split("/:")
        normal_path = "\\".join(normal_path)
        return normal_path


class RecordSong(Song):
    """Represents a song, in recordbox format"""

    def __init__(self, id: str, name: str, record_path: str, **kwargs):
        super().__init__(name)
        self.id = id
        self.path = Song.record_path_to_normal_path(record_path)
        self.record_path = record_path
        self.file_name = self.path.split("\\")[-1]

        if "size" in kwargs:
            self.size = kwargs["size"]


class TraktorSong(Song):
    """Represents a song, in traktor format"""

    def __init__(self, name: str, traktor_path: str):
        super().__init__(name)
        self.traktor_path = traktor_path
        self.path = Song.traktor_path_to_normal_path(traktor_path)


class Playlist:
    """Represents a playlist, in normal format"""

    def __init__(self, name: str, songs: Iterable[RecordSong]):
        self.name = name
        self.songs = songs

    def get_nb_entries(self):
        return len(self.songs)

    nb_entries = property(get_nb_entries)

    def __str__(self):
        """Representation in a string"""
        return str(self.name)

    def __repr__(self):
        """Representation in an array"""
        return self.__str__()


class Parser(Debug):
    """
    Base Class for a Parser

    Has xml.etree.ElementTree objects that represents the xml tree:
        - playlists_tree : the playlist of the collection
        - songs_tree : the songs of the collection

    Each parser has its own method to modifiy the xml objects to add/remove/insert playlists/songs
    A save of the xml tree object result of the updated xml for the software

    The playlists and the songs are also represented by arrays (songs and playlists)
    These arrays are used as an interface to communicate songs and playlists to others parsers

    """

    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_path = path

        # XML Parser
        self.tree = ET.parse(path)
        self.playlists_tree = None
        self.songs_tree = None

        # Songs and playlist attributes
        self.songs = []
        self.playlists = []

        # Init these attributes
        self.get_songs_and_playlists()

    @abstractmethod
    def get_songs_and_playlists(self):
        """
        Parse xml to init following objects:

            - playlists_tree (ET)
            - songs_tree (ET)
            - playlists (list)
            - songs (list)
        """
        pass

    @abstractmethod
    def add_playlist_to_tree(self, playlist: Playlist, index=None):
        """
        Update playlists_tree with a new playlist
        Append information needed by software to add a new playlist in the collection
        """
        pass

    def add_playlists_to_tree(self, playlists: Iterable[Playlist]):
        for playlist in playlists:
            self.add_playlist_to_tree(playlist)

    def save_file(self, file_path: str = None, backup: bool = True):
        """
        Save XML or NML file
        If no path specified, take the path of the initialization of the parser object
        If backup == True, copy the file used for initialization and add ".bak"
        """
        if file_path is None:
            file_path = self.file_path
        if backup:
            shutil.copy(self.file_path, self.file_path + ".bak")

        self._save_tree(file_path)

    @abstractmethod
    def _save_tree(self, file_path: str):
        """
        Specific method to save the collection file
        It depends on the software
        """
        pass


class TraktorParser(Parser):
    """
    Represents the collection.nml file:
        - All songs in the collection
        - Associated playlists
        - Add/Remove playlits
        - Save XML
    """

    def __init__(self, path, verbose=False):
        print("Initializing Traktor Parser ...")
        super().__init__(path, verbose)

    def get_songs_and_playlists(self):
        root = self.tree.getroot()
        self.playlists = []
        self.songs = []
        # Use of a dict to find the song by its file path (KEY)
        songs_dict = {}
        for child in root:
            if child.tag == "COLLECTION":
                self.songs_tree = child
                for song in child:
                    # TODO : Get more info : CUE, Score, Comment...
                    name = song.attrib["TITLE"]
                    # print(name)
                    for elmt in song:
                        if elmt.tag == "LOCATION":
                            traktor_path = (
                                elmt.attrib["VOLUME"]
                                + elmt.attrib["DIR"]
                                + elmt.attrib["FILE"]
                            )
                            # print(traktor_path)
                    traktor_song = TraktorSong(name, traktor_path)
                    self.songs.append(traktor_song)
                    songs_dict[traktor_path] = traktor_song
            if child.tag == "PLAYLISTS":
                for node in child:
                    for subnodes in node:
                        # There is only one subnodes elements
                        self.playlists_tree = subnodes
                        # print(subnodes.attrib)
                        # subnodes.attrib["COUNT"] = nb_playlists
                        for node in subnodes:
                            playlist_songs = []
                            # print(node.attrib)
                            name = node.attrib["NAME"]
                            for playlist in node:
                                # print(playlist.attrib)
                                nb_element = playlist.attrib["ENTRIES"]
                                for entry in playlist:
                                    # print(entry.attrib)
                                    for primarykey in entry:
                                        # print(primarykey.attrib)
                                        traktor_track_path = primarykey.attrib["KEY"]
                                        playlist_songs.append(
                                            songs_dict[traktor_track_path]
                                        )

                            traktor_playlist = Playlist(name, playlist_songs)
                            self.playlists.append(traktor_playlist)
                            self.print(
                                f"Found playlist : {traktor_playlist} | Nb songs: {traktor_playlist.nb_entries}"
                            )

    def add_playlist_to_tree(self, playlist: Playlist, index=None):
        # Create playlist NML structure
        node = ET.Element("NODE")
        node.set("TYPE", "PLAYLIST")
        node.set("NAME", playlist.name)
        playlist_xml = ET.SubElement(node, "PLAYLIST")
        playlist_xml.set("ENTRIES", str(playlist.nb_entries))
        playlist_xml.set("TYPE", "LIST")
        playlist_xml.set("UUID", str(uuid.uuid1()).replace("-", ""))
        # Add songs
        for song in playlist.songs:
            self.add_traktor_track_to_playlist(playlist_xml, song)

        # Take last index before playlist _LOOPS and _RECORDINGS
        ending_playlists = [
            playlist
            for playlist in self.playlists
            if playlist.name in ["_LOOPS", "_RECORDINGS"]
        ]
        if len(ending_playlists):
            max_index = min(
                [self.playlists.index(playlist) for playlist in ending_playlists]
            )
        else:
            # If _LOOPS or _RECORDINGS doesn't exist, take the last index
            max_index = len([x for x in self.playlists_tree])

        if index is None:
            index = max_index
        elif index > max_index:
            index = max_index

        # Insert playlist to tree
        self.playlists_tree.insert(index, node)
        # Also insert playlist to playlist array
        self.playlists.insert(index,playlist)

    def add_traktor_track_to_collection(
        self, collection_parent: ET.SubElement, song: RecordSong
    ):
        """
        Useless for now
        Create the NML structure of a track for the collection
        """
        # key = RecordSong.path_to_traktor(song.path)
        # track_entry = ET.SubElement(playlist_parent, "ENTRY")
        # track_entry.tail = "\n"
        # track_primary_key = ET.SubElement(track_entry, "PRIMARYKEY")
        # track_primary_key.set("TYPE", "TRACK")
        # track_primary_key.set("KEY", key)
        # # To add a line return, NML format exigence
        # track_primary_key.tail = "\n"

        X = ""

        # <ENTRY MODIFIED_DATE="2022/2/6" MODIFIED_TIME="7669" AUDIO_ID="AcMCRVVlVWVVVVVVZVZVREVVVVVlVmVmVWVWZVRVZVZVZlZlVlVmVmZlVVVVVVVVVVVVVVVVWLmZmqmZmaqZmZmZmaqampqpmpmqmZqpZ3d3mqmZuZmampmZmqmpmqqqqqqqqqqqqqqHiIh2Z2ZmZmZ2QzMzMzMzWIiIiYiIiIiIiJiIiHeIiImIiIiYiZiIiZmJiZmImZmIiZmZmImYiZmZmZmamZmZmZmZlndVVVVVVVVmZmZmZmZnZmZmZmZmZ2Z3d3d3eJmZmamZmZqZmZmZmZmpmZmpmZmamZmZd3d3dVVVVVVVVVZmZmVWZmVEREREREQzMzMzMzIQAAAAAA==" TITLE="Brainchild (Original)" ARTIST="Nostrum"><LOCATION DIR="/:Users/:Nono/:Music/:MIX/:HARDTRANCE/:" FILE="nostrum-brainchild-1996.mp3" VOLUME="C:" VOLUMEID="32a20fa3"></LOCATION>
        # <ALBUM TITLE="The Singles Collection"></ALBUM>
        # <MODIFICATION_INFO AUTHOR_TYPE="user"></MODIFICATION_INFO>
        # <INFO BITRATE="230000" COVERARTID="112/QLHLHWCAH1N4GCX1P5OTBKJN3LFB" PLAYTIME="450" IMPORT_DATE="2022/2/5" FLAGS="10" FILESIZE="12868"></INFO>
        # <TEMPO BPM="164.990662" BPM_QUALITY="100.000000"></TEMPO>
        # <LOUDNESS PERCEIVED_DB="0.000000"></LOUDNESS>

        # ENTRY element that contains all other subelements
        entry = ET.Element("ENTRY")
        entry.set("MODIFIED_DATE", X)
        entry.set("AUDIO_ID", X)
        entry.set("TITLE", X)
        entry.set("ARTIST", X)

        # LOCATION subelement
        location = ET.SubElement(entry, "LOCATION")
        # Change values to split path and add volume ID
        # location.set("DIR", song.normal_path_to_traktor_path(song.path))
        # location.set("FILE", song.normal_path_to_traktor_path(song.path))
        # location.set("VOLUME", song.normal_path_to_traktor_path(song.path))
        # location.set("VOLUMEID", song.normal_path_to_traktor_path(song.path))

        # test if this info is enough, else add:

        # # ALBUM subelement
        # album=ET.SubElement(entry,"ALBUM")
        # album.set("TITLE",X)

        # # MODIFICATION_INFO subelement
        # modification_info=ET.SubElement(entry,"MODIFICATION_INFO")
        # modification_info.set("AUTHOR_TYPE","user")

        # ...
        pass

    def add_traktor_track_to_playlist(
        self, playlist_parent: ET.SubElement, song: TraktorSong
    ):
        """Create the NML structure of a track for a playlist"""
        key = Song.normal_path_to_traktor_path(song.path)
        track_entry = ET.SubElement(playlist_parent, "ENTRY")
        track_entry.tail = "\n"
        track_primary_key = ET.SubElement(track_entry, "PRIMARYKEY")
        track_primary_key.set("TYPE", "TRACK")
        track_primary_key.set("KEY", key)
        # Add a line return, NML format exigence
        track_primary_key.tail = "\n"

    def get_playlists_from_tree(self, return_track: bool = False):
        """Mainly used for control after adding a playlist to tree"""
        for playlist in self.playlists_tree:
            print(playlist.attrib["NAME"])
            if return_track:
                for abcd in playlist:
                    # print(abcd.attrib)
                    # {'ENTRIES': '1', 'TYPE': 'LIST', 'UUID': 'b5db9c6746634c1890bb53becfe90ad5'}
                    for abc in abcd:
                        # print(abc.attrib)
                        # {}
                        for ab in abc:
                            print(ab.attrib["KEY"])
                            # {'TYPE': 'TRACK', 'KEY': 'C:/:Users/:Nono/:Music/:MIX/:10 - ORGANIK/:SATSANG - SUMIRUNA.mp3'}

    def _save_tree(self, file_path: str):
        """Save collection file"""
        self.tree.write(
            file_path,
            encoding="utf-8",
            xml_declaration=True,
            short_empty_elements=False,
        )
        self.print("Collection file saved!")


class RecordBoxParser(Parser):
    """
    Represents the recordbox.xml file:
        - All songs in the collection
        - Associated playlists
        - Add/Remove playlists
        - Save XML
    """

    def __init__(self, path, verbose=False):
        print("Initializing RecordBox Parser ...")
        super().__init__(path, verbose)

    def get_songs_and_playlists(self):
        root = self.tree.getroot()
        songs_dict = {}
        for child in root:
            if child.tag == "COLLECTION":
                # To simplify add/remove of songs in collection
                # Init location of songs in XML
                self.songs_tree = child
                for ch in child:
                    # The childs of collection are songs
                    song = RecordSong(
                        ch.attrib["TrackID"],
                        ch.attrib["Name"],
                        ch.attrib["Location"],
                        size=int(ch.attrib["Size"]),
                    )
                    self.songs.append(song)
                    songs_dict[song.id] = song
            if child.tag == "PLAYLISTS":
                for node_root in child:
                    # To simplify add/remove of playlists in collection
                    # Init location of playlists in XML
                    self.playlists_tree = node_root
                    for playlist in node_root:
                        # print(playlist.attrib["Name"])
                        songs_id = [song.attrib["Key"] for song in playlist]
                        songs = [songs_dict[id] for id in songs_id]
                        # print(songs_id)
                        recordbox_playlist = Playlist(playlist.attrib["Name"], songs)
                        self.playlists.append(recordbox_playlist)
                        self.print(
                            f"Found playlist : {recordbox_playlist} | Nb songs: {recordbox_playlist.nb_entries}"
                        )

    def add_song_to_tree(self, song: RecordSong):
        """Not used for now"""
        pass

    def add_playlist_to_tree(self, playlist: Playlist, index=None):
        # Create playlist element:
        node = ET.Element("NODE")
        # <NODE Name="01 - ELECTRO" Type="1" KeyType="0" Entries="99">
        node.set("Name", playlist.name)
        node.set("Type", "1")
        node.set("KeyType", "0")
        node.set("Entries", str(playlist.nb_entries))

        # Add songs to playlist
        for song in playlist.songs:
            # If song is from Traktor
            if isinstance(song, TraktorSong):
                song = Exporter.convert_traktor_song_to_recordbox(song, self)
            track = ET.SubElement(node, "TRACK")
            # <TRACK Key="69731364"/>
            track.set("Key", song.id)
            track.tail = "\n"

        # Add playlist element to tree
        if index is None:
            # If no index specified, put element at last index
            index = len([x for x in self.playlists_tree])
       
        # Insert playlist to tree
        self.playlists_tree.insert(index, node)
        # Also insert playlist to playlist array
        self.playlists.insert(index,playlist)

    def get_playlists_from_tree(self, return_track: bool = False):
        """Mainly used for control after adding a playlist to tree"""
        for playlist in self.playlists_tree:
            print(playlist.attrib["Name"])
            if return_track:
                for abcd in playlist:
                    print(abcd.attrib)
                    # {'Key': '31926856'}

    def _save_tree(self, file_path: str):
        """Save XML"""
        self.tree.write(file_path, encoding="utf-8", xml_declaration=True)
        self.print("Collection file saved!")


class Exporter:
    @classmethod
    def check_playlist_folders_exists(
        cls, root_folder: str, playlists: Iterable[Playlist]
    ):
        folder_list = os.listdir(root_folder)
        if len(folder_list) != 0:
            answer = input(
                f"Warning, followings folders exists:\n{folder_list}\nDo you want to continue ?\n [Y/y/Yes/yes = yes | other = no]"
            )
            if answer.lower() not in ["y", "yes"]:
                raise Exception("Processus aborded")

    @classmethod
    def create_playlist_folder(cls, root_folder: str, playlist: Playlist):
        playlist_folder = os.path.join(root_folder, playlist.name)
        print(f"Create folder {playlist_folder} inside {root_folder}")
        # os.makedirs(playlist_folder)

    @classmethod
    def copy_songs_to_playlist_folders(
        cls, target_dir: str, playlists: Iterable[Playlist]
    ):
        copied_size = 0
        # TODO : Change sum calculation
        total_size = sum(
            [song.size for playlist in playlists for song in playlist.songs]
        )
        total_size_mb = total_size / (1024 * 1024)
        print(f"Total playlists size: {total_size_mb:.2f} Mb")
        for playlist in playlists:
            playlist_folder = os.path.join(target_dir, playlist.name)
            Exporter.create_playlist_folder(playlist_folder)
            for song in playlist.songs:
                source_path = song.path
                dst_path = os.path.join(playlist_folder, song.file_name)
                print(f"Copying song {song.file_name} to {playlist_folder}")
                # shutil.copy(source_path, dst_path)
                copied_size += song.size
                print(f"On work... : {copied_size/total_size*100:.2f} %")

    @classmethod
    def convert_traktor_song_to_recordbox(
        cls, traktor_song: TraktorSong, recordbox_parser: RecordBoxParser
    ):
        # Check if Traktor song exists in RecordBox Collection by searching by path attribute and return RecordSong
        # Raise an exception if the song doesn't exists
        results = [x for x in recordbox_parser.songs if x.path == traktor_song.path]
        if len(results) != 0:
            return results[0]
        else:
            raise Exception(
                f"Traktor Song {traktor_song} doesn't exist in RecordBox Collection. Please add it to collection first"
            )


if __name__ == "__main__":

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
