from be.model import store
from be.model.store import User as UserModel, Store as StoreModel, UserStore, Book as BookModel, NewOrder as NewOrderModel


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()


    def user_id_exist(self, user_id):
        return (
                self.conn.query(UserModel)
                .filter(UserModel.user_id == user_id)
                .first()
                is not None
        )

    def book_id_exist(self, store_id, book_id):
        return (
                self.conn.query(StoreModel)
                .filter(StoreModel.store_id == store_id, StoreModel.book_id == book_id)
                .first()
                is not None
        )

    def book_id_exist_all(self, book_id):
        return (
                self.conn.query(BookModel)
                .filter(BookModel.id == book_id)
                .first()
                is not None
        )

    def store_id_exist(self, store_id):
        return (
                self.conn.query(UserStore)
                .filter(UserStore.store_id == store_id)
                .first()
                is not None
        )
        
    def order_id_exist(self, user_id, order_id):
        return (
                self.conn.query(NewOrderModel)
                .filter(NewOrderModel.user_id == user_id, NewOrderModel.order_id == order_id)
                .first()
                is not None
        )
