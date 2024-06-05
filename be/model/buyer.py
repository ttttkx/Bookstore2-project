import traceback
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from be.model import db_conn
from be.model import error
from be.model.store import NewOrder, NewOrderDetail, User as UserModel, Store as StoreModel


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
            self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            new_order_details = []
            for book_id, count in id_and_count:
                store_data = self.conn.query(StoreModel).filter_by(
                    store_id=store_id,
                    book_id=book_id
                ).first()

                if store_data is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = store_data.stock_level
                price = store_data.price
                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)
                store_data.stock_level -= count

                new_order_detail = NewOrderDetail(
                    order_id=uid,
                    book_id=book_id,
                    count=count,
                    price=price
                )
                new_order_details.append(new_order_detail)

            new_order = NewOrder(
                user_id=user_id,
                store_id=store_id,
                order_id=uid,
                status="unpaid",
                created_at=datetime.now().isoformat()
            )

            self.conn.add_all(new_order_details)
            self.conn.add(new_order)
            self.conn.commit()

            order_id = uid

        except IntegrityError as e:
            return str(e)
        except Exception as e:
            traceback.print_exc()
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id
            

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            order_data = self.conn.query(NewOrder).filter_by(order_id=order_id).first()

            # if order_data is None:
            #     return error.error_invalid_order_id(order_id)

            # if order_data.user_id != user_id:
            #     return error.error_authorization_fail()

            if order_data.status != "unpaid":
                return error.error_status_fail(order_id)

            user_data = self.conn.query(UserModel).filter_by(user_id=user_id).first()
            # if user_data is None:
            #     return error.error_non_exist_user_id(user_id)

            if password != user_data.password:
                return error.error_authorization_fail()

            balance = user_data.balance
            order_detail_data = self.conn.query(NewOrderDetail).filter_by(order_id=order_id).all()
            total_price = sum([order_detail.price * order_detail.count for order_detail in order_detail_data])

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)
            user_data.balance = balance - total_price
            
            order_data.status = "paid"

            self.conn.commit()

        except Exception as e:
            return 530, "{}".format(str(e))

        return 200, "ok"
    
    
    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user_data = self.conn.query(UserModel).filter_by(user_id=user_id).first()

            if user_data is None:
                return error.error_authorization_fail()

            if user_data.password != password:
                return error.error_authorization_fail()

            user_data.balance += add_value

            self.conn.commit()

        except Exception as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 查看历史订单
    def get_buyer_orders(self, user_id: str) -> (int, str, list):
        try:
            orders = self.conn.query(NewOrder).filter_by(user_id=user_id).all()
            buyer_orders = []
            for i in orders:
                buyer_orders.append(
                    {'store_id': i.store_id,
                     'order_id': i.order_id,
                     'status': i.status}
                )
            return 200, "ok", buyer_orders
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        
    # 确认收货
    def receive_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            order_data = self.conn.query(NewOrder).filter_by(order_id=order_id).first()

            if order_data is None:
                return error.error_invalid_order_id(order_id)

            if order_data.user_id != user_id:
                return error.error_authorization_fail()
            if order_data.status == "received":
                return 200, "Order is already received"
            if order_data.status != "shipped":
                return error.error_status_fail(order_id)

            # 更新订单状态为 "received" 并记录收货时间
            order_data.status = "received"
            order_data.received_at = datetime.now().isoformat()
            
            self.conn.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 取消订单
    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            order_data = self.conn.query(NewOrder).filter_by(order_id=order_id).first()

            if order_data is None:
                return error.error_invalid_order_id(order_id)
            if order_data.user_id != user_id:
                return error.error_authorization_fail()
            if order_data.status == "shipped" or order_data.status == "received":
                return error.error_status_fail(order_id)
            if order_data.status == "cancelled":
                return 200, "Order is already cancelled."
            if order_data.status == "paid":
                # 获取订单详细信息
                total_price = 0
                order_details = self.conn.query(NewOrderDetail).filter_by(order_id=order_id).all()
                for order_detail in order_details:
                    count = order_detail.count
                    price = order_detail.price
                    total_price += price * count

                user_data = self.conn.query(UserModel).filter_by(user_id=user_id).first()
                if user_data is None:
                    return error.error_non_exist_user_id(user_id)
                # 计算退款金额
                refund_amount = total_price
                current_balance = user_data.balance
                new_balance = current_balance + refund_amount
                # 更新用户余额
                user_data.balance = new_balance

            # 取消订单，更新状态为 "cancelled"
            order_data.status = "cancelled"
            
            self.conn.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def return_purchase(self, user_id: str, order_id: str) -> (int, str):
        try:
            order_data = self.conn.query(NewOrder).filter_by(order_id=order_id).first()

            if order_data is None:
                return error.error_invalid_order_id(order_id)
            if order_data.user_id != user_id:
                return error.error_authorization_fail()   
            if order_data.status == "returned":
                return 200, "Order is already returned."
            if order_data.status != "received":
                return error.error_status_fail(order_id)
            #计算时间差
            received_at_str = order_data.received_at  
            received_at_dt = datetime.fromisoformat(received_at_str)  
            now_dt = datetime.now()  
            time_difference = now_dt - received_at_dt  
  
            # 检查时间差是否超过70秒  
            if time_difference.total_seconds() > 70:  
                return error.error_status_fail(order_id) 
            # 获取订单详细信息
            total_price = 0
            order_details = self.conn.query(NewOrderDetail).filter_by(order_id=order_id).all()
            for order_detail in order_details:
                count = order_detail.count
                price = order_detail.price
                total_price += price * count

            # 更新用户余额，将付款退还给用户
            user_data = self.conn.query(UserModel).filter_by(user_id=user_id).first()
            if user_data is None:
                return error.error_non_exist_user_id(user_id)

            # 计算退款金额
            refund_amount = total_price
            current_balance = user_data.balance
            new_balance = current_balance + refund_amount
            
            user_data.balance = new_balance
            order_data.status = "returned"
            
            self.conn.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
    


