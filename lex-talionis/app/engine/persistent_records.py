import logging
from app.utilities.data import Data, Prefab

from app.engine import persistent_data

from app.data.database.database import DB

class PersistentRecord(Prefab):
    def __init__(self, nid: str = '', value=None):
        self.nid = nid
        self.value = value

class PersistentRecordManager(Data):
    datatype = PersistentRecord

    def __init__(self, location):
        super().__init__()
        self.location = location

    def get(self, nid):
        if nid in self.keys():
            return super().get(nid).value
        return None

    def create(self, nid, value=None):
        if nid in self.keys():
            logging.info("Record with nid of %s already exists")
            return
        self.append(PersistentRecord(nid, value))
        persistent_data.serialize(self.location, self.save())

    def update(self, nid, value):
        if nid in self.keys():
            record = super().get(nid)
            record.value = value
            persistent_data.serialize(self.location, self.save())
        else:
            logging.info("Record with nid of %s doesn't exist")

    def delete(self, nid):
        if nid in self.keys():
            self.remove_key(nid)
            persistent_data.serialize(self.location, self.save())
        else:
            logging.info("Record with nid of %s doesn't exist")

# Make sure to reload all persistent records whenever we start the engine
game_id = str(DB.constants.value('game_nid'))
location = 'saves/' + game_id + '-persistent_records.p'
data = persistent_data.deserialize(location)
RECORDS = PersistentRecordManager(location)
if data:
    RECORDS.restore(data)
