

import sqlite3
import local_utils.logger as l

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
        self.conn.close()

    def get_cursor(self):
        return self.conn.cursor()

    def drop_db(self):
        cursor = self.get_cursor()
        try:
            cursor.executescript("""
                DROP TABLE IF EXISTS AccessList;
                DROP TABLE IF EXISTS Users;
                DROP TABLE IF EXISTS Cameras;
            """)
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during database deletion: %s", e)
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
            user_id INTEGER UNSIGNED PRIMARY KEY
        );      
        CREATE TABLE IF NOT EXISTS Cameras (
            -- handles the registered cameras, so the cameras which can access the system and are
            camera_id INTEGER PRIMARY KEY,
            camera_name TEXT DEFAULT 'camera_0',
        );      
        CREATE TABLE IF NOT EXISTS AccessList (
        -- handles the access list of the users, so the rooms they can access  
        -- only the authenticated users can access this table, they must insert
        -- the name of the person that can/not access the room
        -- the user_name is a chosen name by the authed user, it can be anything 
        -- to identify the user in the system
            user_name TEXT,
            room_name TEXT,
            listed VARCHAR(1) NOT NULL CHECK(listed IN ('b','w')) DEFAULT 'b',
            PRIMARY KEY (user_name, room_name)
            );
        """
        cursor = self.get_cursor()
        try:
            cursor.executescript(schema_sql)
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during database creation: %s", e)
        finally:
            cursor.close()

        # Esegui le istruzioni SQL (può contenerne più di una)
        return self.conn

    # Get from db
    def user_exist(self, user_id: int) -> bool:
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT COUNT(user_id) FROM Users WHERE user_id=? LIMIT 1", (user_id,))
            user_count = cursor.fetchone()[0]
            return bool(user_count)
        except Exception as e:
            self.logger.error("Error during user selection: %s", e)
        finally:
            cursor.close()

    def user_is_authed(self, user_id: int) -> bool:
        return self.user_exist(user_id)

    def person_already_enrolled(self, user_name: str):
        """Person enrolled in the system, this is not the user"""
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT COUNT(user_name) FROM AccessList WHERE user_name=? LIMIT 1", (user_name,))
            user_count = cursor.fetchone()[0]
            return bool(user_count)
        except Exception as e:
            self.logger.error("Error during user access list selection: %s", e)
        finally:
            cursor.close()

    def get_person_access_list(self, user_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT * FROM AccessList WHERE user_name=?", (user_name,))
            return cursor.fetchall()
        except Exception as e:
            self.logger.error("Error during user access list selection: %s", e)
        finally:
            cursor.close()

    def get_person_access_names(self):
        cursor = self.get_cursor()
        try:
            cursor.execute("SELECT UNIQUE(user_name) FROM AccessList")
            return cursor.fetchall()
        except Exception as e:
            self.logger.error("Error fetching all user names from access list: %s", e)
        finally:
            cursor.close()
    # Add to db
    def add_authed_user(self, user_id: int):
        cursor = self.get_cursor()
        try:
            cursor.execute("INSERT INTO Users VALUES (?)", (user_id,))
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during user insertion: %s", e)
        finally:
            cursor.close()

    def add_person_room_access(self, user_name:str, room_name: str, listed: str = 'b'):
        cursor = self.get_cursor()
        try:
            cursor.execute("INSERT INTO AccessList (user_name, room_name, listed) VALUES (?,?,?)",
                           (user_name, room_name, listed))
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during user insertion: %s", e)
        finally:
            cursor.close()

    # Update db
    def update_person_access_list(self, user_name: str, room_name: str, listed: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("UPDATE AccessList SET listed=? WHERE user_name=? AND room_name=?", (listed, user_name, room_name))
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during listed update: %s", e)
        finally:
            cursor.close()

    def update_person_access_name(self, old_user_name: int, new_user_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("UPDATE AccessList SET user_name=? WHERE user_name=?", (new_user_name, old_user_name))
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during user name update: %s", e)
        finally:
            cursor.close()

    def update_room_name(self, old_room_name: str, new_room_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("UPDATE AccessList SET room_name=? WHERE room_name=?", (new_room_name, old_room_name))
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during room name update: %s", e)
        finally:
            cursor.close()

    # Delete from db
    def delete_person_access_room(self, user_name: str, room_name: str):
        cursor = self.get_cursor()
        try:
            cursor.execute("DELETE FROM AccessList WHERE user_name=? AND room_name=?", (user_name, room_name))
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during user deletion: %s", e)
        finally:
            cursor.close()

    def delete_user(self, user_id: int):
        cursor = self.get_cursor()
        try:
            cursor.execute("DELETE FROM AccessList WHERE user_id=?", (user_id,))
            self.conn.commit()
        except Exception as e:
            self.logger.error("Error during user deletion: %s", e)
        finally:
            cursor.close()

if __name__ == "__main__":
    # example usage
    db = TBDatabase("/tmp/my_database.db", drop_db=True)
    with db() as db:
        db.add_authed_user(69420)
        db.add_person_room_access('mr2', "room1", 'b')
        db.update_person_access_list('mr2', "room1", 'w')
        print(db.user_exist(1), db.user_exist(69420))
    print('Done')
