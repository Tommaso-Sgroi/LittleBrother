import sqlite3
import local_utils.logger as l

def get_database(db_path, *, dropdb = False):
    return TBDatabase(db_path, dropdb)

UNKNOWN_SPECIAL_USER = u'Unknown\U00002753'

def raise_error(e:Exception, context: str):
    e.add_note(context)
    raise e

class TBDatabase(l.Logger):
    """
    Classe per la gestione di un database SQLite3 per il bot Telegram.

    Users Table:
        handles the registered users, so the users which can access the system and are
        authenticated via the telegram bot
        the user_id is the telegram user id

    AccessList Table:
        handles the access list of the users, so the rooms they can access
        only the authenticated users can access this table, they must insert
        the name of the person that can/not access the room
        the user_name is a chosen name by the authed user, it can be anything
        to identify the user in the system
    """

    def __init__(self, db_path: str, drop_db: bool = False):
        super().__init__(self.__class__.__name__)
        self.db_path = db_path

        with TDBAtomicConnection(self.db_path) as transaction:
            if drop_db:
                transaction.drop_db()
            transaction.create_database()

    def __call__(self, *args, **kwargs):
        return TDBAtomicConnection(self.db_path)


class TDBAtomicConnection(l.Logger):
    """
    This class is necessary to handle the fact that the telegram bot spawn multiple threads and
     sqlite3 doesn't really like that.
    """
    def __init__(self, db_path: str):
        super().__init__(self.__class__.__name__)
        self.conn = sqlite3.connect(db_path)

    def __enter__(self):
        self.cursor = self.get_cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()

    def get_cursor(self):
        return self.conn.cursor()

    def setup_database(self, cameras_ids: list[int], cameras_names: list[str]):
        assert len(cameras_names) == len(cameras_ids)
        # setup special users
        cameras_ids_names = self.get_cameras()

        db_camera_ids = {c_id_n[0] for c_id_n in cameras_ids_names}
        # db_camera_names = {c_id_n[1] for c_id_n in cameras_ids_names}
        cameras_ids = {c_id for c_id in cameras_ids}
        for camera_id, camera_name in zip(cameras_ids, cameras_names):
            if camera_id not in db_camera_ids:
                self.add_camera(camera_id, camera_name)
                db_camera_ids.add(camera_id)
            self.update_camera_name(camera_id, camera_name)

        remove_cameras = db_camera_ids - cameras_ids
        for camera_id in remove_cameras:
            self.delete_camera(camera_id)
        try:
            self.add_enrolled_person(UNKNOWN_SPECIAL_USER)
        except Exception as e:
            pass
        return

    def drop_db(self):
        cursor = self.get_cursor()
        try:
            cursor.executescript("""
                DROP TABLE IF EXISTS AccessList;
                DROP TABLE IF EXISTS Users;
                DROP TABLE IF EXISTS Cameras;
                -- DROP TABLE IF EXISTS EnrolledPeople;
            """)
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during database deletion: %s", e)
            raise_error(e, "Error during database deletion")
        finally:
            cursor.close()

    def create_database(self) -> sqlite3.Connection:
        """
        Crea un database sqlite3 a partire da uno schema di tabelle,
        eseguendo i comandi SQL necessari.
        """
        schema_sql = """        
        CREATE TABLE IF NOT EXISTS Users (
            -- handles the registered users, so the users which can access the system and are 
            -- authenticated via the telegram bot
            -- the user_id is the telegram user id
            user_id INTEGER  PRIMARY KEY
        );
        /*      
        CREATE TABLE IF NOT EXISTS EnrolledPeople (
            -- registers the names of the people enrolled in the system
            user_name TEXT PRIMARY KEY
        );
        */
              
        CREATE TABLE IF NOT EXISTS Cameras (
            -- handles the registered cameras, so the cameras which can access the system and are
            camera_id INTEGER  PRIMARY KEY,
            camera_name TEXT UNIQUE
        );      
        CREATE TABLE IF NOT EXISTS AccessList (
        -- handles the access list of the users, so the rooms they can access  
        -- only the authenticated users can access this table, they must insert
        -- the name of the person that can/not access the room
        -- the user_name is a chosen name by the authed user, it can be anything 
        -- to identify the user in the system
            user_name TEXT,
            camera_id INTEGER , 
            listed VARCHAR(1) NOT NULL CHECK(listed IN ('b','w', 'f')) DEFAULT 'b', -- f means free for all
            FOREIGN KEY (camera_id) REFERENCES Cameras(camera_id) ON DELETE CASCADE,
            -- FOREIGN KEY (user_name) REFERENCES EnrolledPeople(user_name) ON DELETE CASCADE,
            PRIMARY KEY (user_name, camera_id)
            );
        """
        cursor = self.get_cursor()
        try:
            cursor.executescript(schema_sql)
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during database creation: %s", e)
            raise_error(e, "Error during database creation")
        finally:
            cursor.close()

        # Esegui le istruzioni SQL (può contenerne più di una)
        return self.conn

    # Get from db
    def has_access_to_room(self, user_name: str, camera_id: int) -> bool:
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT COUNT(camera_id) FROM AccessList WHERE listed = 'w' AND camera_id=? AND user_name=? LIMIT 1", (camera_id, user_name))
            listed = cursor.fetchone()[0]
            return bool(listed)
        except Exception as e:
            self.logger.error("Error during access list selection: %s", e)
            raise_error(e, "Cannot check access to room %s with user %s".format(camera_id, user_name))
        finally:
            cursor.close()

    def get_camera_name(self, camera_id: int) -> str:
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT camera_name FROM Cameras WHERE camera_id=? LIMIT 1", (camera_id,))
            camera_name = cursor.fetchone()[0]
            return camera_name
        except Exception as e:
            self.logger.error("Error during camera name selection: %s", e)
            raise_error(e, "Error during camera name selection %s".format(camera_id))
        finally:
            cursor.close()


    def user_exist(self, user_id: int) -> bool:
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT COUNT(user_id) FROM Users WHERE user_id=? LIMIT 1", (user_id,))
            user_count = cursor.fetchone()[0]
            return bool(user_count)
        except Exception as e:
            self.logger.error("Cannot check user existence: %s", e)
            raise_error(e, "Cannot check user existence %s".format(user_id))
        finally:
            cursor.close()

    def get_users(self):
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT user_id FROM Users")
            return cursor.fetchall()
        except Exception as e:
            self.logger.error("Error during user selection: %s", e)
            raise_error(e, "Error during user selection")
        finally:
            cursor.close()


    def user_is_authed(self, user_id: int) -> bool:
        return self.user_exist(user_id)

    def camera_exist(self, camera_id: int) -> bool:
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT COUNT(camera_id) FROM Cameras WHERE camera_id=? LIMIT 1", (camera_id,))
            camera_count = cursor.fetchone()[0]
            return bool(camera_count)
        except Exception as e:
            self.logger.error("Cannot check if camera exists: %s", e)
            raise_error(e, "Cannot check if camera exists: %s".format(camera_id))
        finally:
            cursor.close()

    def get_cameras(self) -> list[int, str]:
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT camera_id, camera_name FROM Cameras")
            return cursor.fetchall()
        except Exception as e:
            self.logger.error("Error during camera selection: %s", e)
            raise_error(e, "Error during camera selection")
        finally:
            cursor.close()

    def person_already_enrolled(self, user_name: str):
        """Person enrolled in the system, this is not the user"""
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT COUNT(user_name) FROM AccessList WHERE user_name=? LIMIT 1", (user_name,))
            user_count = cursor.fetchone()[0]
            return bool(user_count)
        except Exception as e:
            self.logger.error("Cannot check if the person is already enrolled: %s", e)
            raise_error(e, "Cannot check if the person is already enrolled: %s".format(user_name))
        finally:
            cursor.close()

    def get_person_rooms_access_list(self, user_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("""
                       SELECT user_name, AL.camera_id AS camera_id, camera_name, listed 
                       FROM AccessList AS AL JOIN Cameras AS CM ON AL.camera_id=CM.camera_id  
                       WHERE user_name=?
                        """,(user_name,))
            return cursor.fetchall()
        except Exception as e:
            self.logger.error("Error during user access list selection: %s", e)
            raise_error(e, "Error during user access list selection %s".format(user_name))
        finally:
            cursor.close()

    def get_people_access_names(self):
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT DISTINCT (user_name) AS names FROM AccessList")
            names = cursor.fetchall()
            return [name[0] for name in names]
        except Exception as e:
            self.logger.error("Error fetching all user names from access list: %s", e)
            raise_error(e, "Error fetching all user names from access list")
        finally:
            cursor.close()
    # Add to db
    def add_authed_user(self, user_id: int):
        cursor = self.get_cursor()
        try:
            cursor.execute("INSERT INTO Users VALUES (?)", (user_id,))
        except Exception as e:
            self.logger.error("Error during user insertion: %s", e)
            raise_error(e, "Error during user insertion: %s".format(user_id))
        finally:
            cursor.close()

    def add_person_room_access(self, user_name:str, camera_id: int, listed: str = 'b'):
        cursor = self.get_cursor()
        try:
            cursor.execute("INSERT INTO AccessList (user_name, camera_id, listed) VALUES (?,?,?)",
                           (user_name, camera_id, listed))
        except Exception as e:
            self.logger.error("Error during user insertion: %s", e)
            raise_error(e, "Error during user insertion: username %s, camera_id %s, listed %s".format(user_name, camera_id, listed))
        finally:
            cursor.close()

    def add_camera(self, camera_id: int, camera_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("INSERT INTO Cameras (camera_id, camera_name) VALUES (?, ?)", (camera_id, camera_name,))
            cursor.execute("INSERT INTO AccessList (user_name, camera_id) SELECT DISTINCT (user_name), ? FROM AccessList", (camera_id,))
        except Exception as e:
            self.logger.error("Error during camera insertion: %s", e)
            raise_error(e, "Error during camera insertion: %s %s".format(camera_id, camera_name))
        finally:
            cursor.close()

    def add_enrolled_person(self, user_name: str):
        cursor = self.get_cursor()
        try:
            # cursor.execute("INSERT INTO EnrolledPeople (user_name) VALUES (?)", (user_name,))
            cursor.execute("INSERT INTO AccessList (user_name, camera_id, listed) SELECT ?, camera_id, 'b' FROM Cameras", (user_name,))
        except Exception as e:
            self.logger.error("Cannot enroll person '%s' user insertion: %s", user_name, e)
            raise_error(e, "Cannot enroll person '%s' user insertion".format(user_name))
        finally:
            cursor.close()

    # Update db
    def update_person_access_list(self, user_name: str, camera_id: int, listed: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("UPDATE AccessList SET listed=? WHERE user_name=? AND camera_id=?", (listed, user_name, camera_id))
        except Exception as e:
            self.logger.error("Error during listed update: %s", e)
            raise_error(e, "Error during listed update: %s %s %s".format(user_name, camera_id, listed))
        finally:
            cursor.close()

    def update_person_access_name(self, old_user_name: int, new_user_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("UPDATE AccessList SET user_name=? WHERE user_name=?", (new_user_name, old_user_name))
        except Exception as e:
            self.logger.error("Error during user name update: %s", e)
            raise_error(e, "Error during user name update: %s %s".format(old_user_name, new_user_name))
        finally:
            cursor.close()

    def update_room_name(self, camera_id: int, new_room_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("UPDATE Cameras SET camera_name=? WHERE camera_id=?", (new_room_name, camera_id))
        except Exception as e:
            self.logger.error("Error during room name update: %s", e)
            raise_error(e, "Error during room name update: %s %s".format(camera_id, new_room_name))
        finally:
            cursor.close()

    def update_camera_name(self, camera_id: int, new_camera_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("UPDATE Cameras SET camera_name=? WHERE camera_id=?", (new_camera_name, camera_id))
        except Exception as e:
            self.logger.error("Error during camera name update: %s", e)
            raise_error(e, "Error during camera name update: %s %s".format(camera_id, new_camera_name))
        finally:
            cursor.close()

    # Delete from db
    def delete_person_access_room(self, user_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("DELETE FROM AccessList WHERE user_name=?;", [user_name])
        except Exception as e:
            self.logger.error("Error during enrolled person '%s' deletion: %s", user_name, e)
            raise_error(e, "Error during enrolled person '%s' deletion".format(user_name))
        finally:
            cursor.close()

    def delete_camera(self, camera_id: int):
        cursor = self.get_cursor()
        try:
            cursor.execute("DELETE FROM Cameras WHERE camera_id=?", (camera_id,))
            cursor.execute("DELETE FROM AccessList WHERE camera_id=?", (camera_id,)) # because was not deleted too apparently
        except Exception as e:
            self.logger.error("Error during camera deletion: %s", e)
            raise_error(e, "Error during camera deletion: %s".format(camera_id))
        finally:
            cursor.close()

    def delete_user(self, user_id: int):
        """Do not confuse users with people"""
        cursor = self.get_cursor()
        try:
            cursor.execute("DELETE FROM Users WHERE user_id=?", (user_id,))
        except Exception as e:
            self.logger.error("Error during user deletion: %s", e)
            raise_error(e, "Error during user deletion: %s".format(user_id))
        finally:
            cursor.close()

if __name__ == "__main__":
    # example usage
    db = TBDatabase("./my_database.db", drop_db=True)
    with db() as db:
        db.add_authed_user(69420)
        db.add_camera(1, 'Camera 1')
        db.add_camera(2, 'Camera 2')
        # db.add_person_room_access('mr2', 1, 'b')
        # db.add_person_room_access('mr2', 2, 'b')

        db.add_enrolled_person('mr2')
        db.add_enrolled_person('mr1')
        db.add_enrolled_person('mr3')

        db.add_camera(3, 'Camera 3')


        db.update_person_access_list('mr2', 2, 'w')
        print(db.user_exist(1), db.user_exist(69420))
    print('Done')
