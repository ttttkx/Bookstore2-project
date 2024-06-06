import traceback
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from be.model import db_conn
from be.model import error
from be.model.store import NewOrder, NewOrderDetail, User as UserModel, Store as StoreModel
from be.model.user import User
import random
from fe import conf

province_postage = {
    "上海": 0, "江苏": 0, "浙江": 0, "山西": 5, "内蒙古": 5, "辽宁": 5, "吉林": 5, "黑龙江": 5, "北京": 5, 
    "天津": 5, "河北": 5, "安徽": 5, "福建": 5, "江西": 5, "山东": 5, "河南": 5, "湖北": 5, "湖南": 5, 
    "广东": 5, "广西": 5, "海南": 5, "重庆": 5, "四川": 5, "贵州": 5, "云南": 5, "宁夏": 5, "陕西": 5, 
    "甘肃": 10, "青海": 10, "西藏": 10, "新疆": 10, "台湾": 15, "香港": 15, "澳门": 15
}


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
            
            if not self.user_address_exist(user_id):
                return error.error_non_exist_address(user_id) + (order_id,)           
            
            user_address = (self.conn.query(UserModel).filter_by(user_id = user_id).first()).address     

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
                
                store_data.sale_amount += count            

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
                shipped_at = None,
                received_at = None,
                created_at=datetime.now().isoformat(),
                address=user_address                                  
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
        
#打折接口
    def discount(self, user_id: str, order_id: str):
        try:
            order_data = self.conn.query(NewOrder).filter_by(order_id=order_id).first()
            
            if order_data is None:
                return error.error_invalid_order_id(order_id)

            if order_data.user_id != user_id:
                return error.error_authorization_fail()

            if order_data.status != "unpaid":
                return error.error_status_fail(order_id)
            
            order_detail_data = self.conn.query(NewOrderDetail).filter_by(order_id=order_id).all()
            total_price = sum([order_detail.price * order_detail.count for order_detail in order_detail_data])
            
            total_count = 0
            for order_detail in order_detail_data:
                total_count += order_detail.count           
            if(total_count > 3):
                total_price *= 0.9
            elif(total_count > 5):
                total_price *= 0.8
            elif(total_price > 10):
                total_price *= 0.6
                
            return 200, total_price
                                            
        except Exception as e:
            return 530, "{}".format(str(e))
        
#邮费接口
    def postage(self, user_id: str, order_id: str):           
        try:
            order_data = self.conn.query(NewOrder).filter_by(order_id=order_id).first()
            
            if order_data is None:
                return error.error_invalid_order_id(order_id)

            if order_data.user_id != user_id:
                return error.error_authorization_fail()

            if order_data.status != "unpaid":
                return error.error_status_fail(order_id)
            
            _postage = 0
            user_address = order_data.address
            for province, postage in province_postage.items():
                if(province == user_address):
                    _postage = postage
                
            return 200, _postage

                                           
        except Exception as e:
            return 530, "{}".format(str(e))
            
            
#推荐接口
    def recommend(self, store_id: str, order_id: str):     
        try:
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)           
            
            store_data = self.conn.query(StoreModel).filter_by(store_id=store_id).all()
            best_sale_books = []
            sale_amount = 0
            for book_data in store_data:
                if(book_data.sale_amount is not None and book_data.sale_amount >= sale_amount):
                    sale_amount = book_data.sale_amount
                    
            for book_data in store_data:
                if(book_data.sale_amount == sale_amount and book_data.stock_level > 0):
                    best_sale_books.append(book_data)
            
            order_detail_exist = 1
            count = 0
            while(order_detail_exist and count < 1000):
                store_data = random.choice(best_sale_books)
                order_detail_exist = (
                    self.conn.query(NewOrderDetail)
                    .filter_by(order_id=order_id, book_id=store_data.book_id)
                    .first()
                    is not None
                    )
                count += 1
                
            if(order_detail_exist == 0):
                new_order_detail = NewOrderDetail(
                    order_id=order_id,
                    book_id=store_data.book_id,
                    count=1,
                    price=store_data.price
                )

                self.conn.add(new_order_detail)
                self.conn.commit()

            return 200, store_data.sale_amount
                                            
        except Exception as e:
            return 530, "{}".format(str(e))
        

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            order_data = self.conn.query(NewOrder).filter_by(order_id=order_id).first()

            if order_data is None:
                return error.error_invalid_order_id(order_id)

            if order_data.user_id != user_id:
                return error.error_authorization_fail()

            if order_data.status != "unpaid":
                return error.error_status_fail(order_id)

            user_data = self.conn.query(UserModel).filter_by(user_id=user_id).first()
            if user_data is None:
                return error.error_non_exist_user_id(user_id)

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
                total_price = 0
                order_details = self.conn.query(NewOrderDetail).filter_by(order_id=order_id).all()
                for order_detail in order_details:
                    count = order_detail.count
                    price = order_detail.price
                    total_price += price * count

                user_data = self.conn.query(UserModel).filter_by(user_id=user_id).first()
                if user_data is None:
                    return error.error_non_exist_user_id(user_id)

                refund_amount = total_price
                current_balance = user_data.balance
                new_balance = current_balance + refund_amount

                user_data.balance = new_balance

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
            received_at_str = order_data.received_at
  
            received_at_dt = datetime.fromisoformat(received_at_str)  
  
            now_dt = datetime.now()  
  
            time_difference = now_dt - received_at_dt  
  
            if time_difference.total_seconds() > 70:  
                return error.error_status_fail(order_id) 

            total_price = 0
            order_details = self.conn.query(NewOrderDetail).filter_by(order_id=order_id).all()
            for order_detail in order_details:
                count = order_detail.count
                price = order_detail.price
                total_price += price * count

            user_data = self.conn.query(UserModel).filter_by(user_id=user_id).first()
            if user_data is None:
                return error.error_non_exist_user_id(user_id)

            refund_amount = total_price
            current_balance = user_data.balance
            new_balance = current_balance + refund_amount

            user_data.balance = new_balance

            order_data.status = "returned"
            
            self.conn.commit()
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
