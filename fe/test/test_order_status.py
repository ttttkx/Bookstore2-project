import pytest
import time
from fe.access.seller import ship_order
from fe.access.buyer import Buyer
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
import uuid
from fe.access.book import Book


class TestOrderStatus:
    seller_id: str
    store_id: str
    buyer_id: str
    password: str
    buy_book_info_list: [Book]
    total_price: int
    order_id: str
    buyer: Buyer

    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.seller_id = "test_order_status_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_order_status_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_order_status_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id

        gen_book = GenBook(self.seller_id, self.store_id)
        ok, buy_book_id_list = gen_book.gen(
            non_exist_book_id=False, low_stock_level=False, max_book_count=5
        )
        self.buy_book_info_list = gen_book.buy_book_info_list
        assert ok
        
        self.buyer = register_new_buyer(self.buyer_id, self.password)      
        code, self.order_id = self.buyer.new_order(self.store_id, buy_book_id_list)   
        assert code == 200

        order_info=self.buyer.get_order_info(self.order_id)    
        assert order_info['status'] == 'unpaid'

        self.total_price = 0
        for item in self.buy_book_info_list:
            book: Book = item[0]
            num = item[1]
            if book.price is None:
                continue
            else:
                self.total_price += book.price * num
        yield

    def test_ok(self):
        code = self.buyer.add_funds(self.total_price)     
        assert code == 200

        code = self.buyer.payment(self.order_id)        
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)  
        assert order_info['status'] == 'paid'

        code = ship_order(self.store_id,self.order_id)
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)     
        assert order_info['status'] == 'shipped'

        code = self.buyer.receive_order(self.order_id)    
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] == 'received'
        
    def test_error_non_exist_store_id(self):                                      
        code = self.buyer.add_funds(self.total_price)     
        assert code == 200

        code = self.buyer.payment(self.order_id)        
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)  
        assert order_info['status'] == 'paid'
        
        new_store_id = "test_order_status_store_id_{}".format(str(uuid.uuid1()))
        code = ship_order(new_store_id,self.order_id)
        assert code != 200
        
    
    def test_cancel_unpaid(self):
        code = self.buyer.cancel_order(self.order_id)   
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] == 'cancelled'

        code = ship_order(self.store_id,self.order_id)
        assert code != 200

        code = self.buyer.receive_order(self.order_id) 
        assert code != 200


    def test_cancel_paid(self):
        code = self.buyer.add_funds(self.total_price)     
        assert code == 200

        code = self.buyer.payment(self.order_id)        
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)  
        assert order_info['status'] == 'paid'

        code = self.buyer.cancel_order(self.order_id)   
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] == 'cancelled'

        code = ship_order(self.store_id,self.order_id)
        assert code != 200

        code = self.buyer.receive_order(self.order_id) 
        assert code != 200
#退货
    def test_return_ok(self):
        code = self.buyer.add_funds(self.total_price)     
        assert code == 200

        code = self.buyer.payment(self.order_id)        
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)  
        assert order_info['status'] == 'paid'

        code = ship_order(self.store_id,self.order_id)
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)     
        assert order_info['status'] == 'shipped'

        code = self.buyer.receive_order(self.order_id)    
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] == 'received'

        code = self.buyer.return_purchase(self.order_id) 
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] == 'returned'

#逾期退货
    def test_return_overdue(self):
        code = self.buyer.add_funds(self.total_price)     
        assert code == 200

        code = self.buyer.payment(self.order_id)        
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)  
        assert order_info['status'] == 'paid'

        code = ship_order(self.store_id,self.order_id)
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)     
        assert order_info['status'] == 'shipped'

        code = self.buyer.receive_order(self.order_id)    
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] == 'received'

        time.sleep(80)

        code = self.buyer.return_purchase(self.order_id) 
        assert code != 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] != 'returned'

#未收货就退货
    def test_return_before_received(self):
        code = self.buyer.add_funds(self.total_price)     
        assert code == 200

        code = self.buyer.payment(self.order_id)        
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)  
        assert order_info['status'] == 'paid'

        code = ship_order(self.store_id,self.order_id)
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id)     
        assert order_info['status'] == 'shipped'

        code = self.buyer.return_purchase(self.order_id) 
        assert code != 200
        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] != 'returned'

    def test_ship_before_pay(self):
        code = ship_order(self.store_id,self.order_id)
        assert code != 200

        code = self.buyer.receive_order(self.order_id)   
        assert code != 200

    def test_receive_before_ship(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200

        code = self.buyer.payment(self.order_id)
        assert code == 200
        order_info=self.buyer.get_order_info(self.order_id) 
        assert order_info['status'] == 'paid'

        code = self.buyer.receive_order(self.order_id)  
        assert code != 200
        
    def test_error_non_exist_order_id(self):                 
        new_order_id = "test_order_status_order_id_{}".format(str(uuid.uuid1()))
        code = self.buyer.cancel_order(new_order_id)   
        assert code != 200
        
    def test_auto_cancel(self):
        time.sleep(70)

        order_info=self.buyer.get_order_info(self.order_id)
        assert order_info['status'] == 'cancelled'


