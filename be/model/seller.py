import json
from sqlalchemy.exc import IntegrityError
from be.model import error
from be.model import db_conn
from be.model.store import Store as StoreModel, Book as BookModel, UserStore, NewOrder


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
            self,
            user_id: str,
            store_id: str,
            book_id: str,
            book_json_str: str,
            stock_level: int,
    ):
        book_info=json.loads(book_json_str)
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_info['id']):
                return error.error_exist_book_id(book_info['id'])
            
            if self.book_id_exist_all(book_info['id']):
                new_store = StoreModel(
                    store_id=store_id,
                    book_id=book_id,
                    price=book_info["price"],
                    stock_level=stock_level
                )

                self.conn.add(new_store)
                self.conn.commit()
            else:
                new_book = BookModel(
                    id=book_info['id'],
                    title=book_info["title"],
                    author=book_info["author"],
                    publisher=book_info["publisher"],
                    original_title=book_info["original_title"],
                    translator=book_info["translator"],
                    pub_year=book_info["pub_year"],
                    pages=book_info["pages"],
                    price=book_info["price"],
                    currency_unit=book_info["currency_unit"],
                    binding=book_info["binding"],
                    isbn=book_info["isbn"],
                    author_intro=book_info["author_intro"],
                    book_intro=book_info["book_intro"],
                    content=book_info["content"],
                    tags=book_info["tags"],
                )

                new_store = StoreModel(
                    store_id=store_id,
                    book_id=book_info['id'],
                    price=book_info["price"],
                    stock_level=stock_level
                )

                self.conn.add_all([new_book, new_store])
                self.conn.commit()

        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
            self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            store_data = self.conn.query(StoreModel).filter_by(store_id=store_id, book_id=book_id).first()
            store_data.stock_level += add_stock_level
            self.conn.commit()

        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            # if not self.user_id_exist(user_id):
            #     return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            new_user_store = UserStore(
                store_id=store_id,
                user_id=user_id
            )

            self.conn.add(new_user_store)
            self.conn.commit()

        except IntegrityError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"


