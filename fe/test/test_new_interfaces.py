import time

import pytest

from fe.access.new_seller import register_new_seller
from fe.access import book
from fe.access.seller import ship_order
from fe.access.buyer import Buyer
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
import uuid
from fe.access.book import Book
from fe.access.auth import Auth
from fe.access import auth
from fe import conf

import random

provinces = ['北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江', '上海', '江苏',
             '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南', '广东',
             '广西', '海南', '重庆', '四川', '贵州', '云南', '西藏', '陕西', '甘肃',
             '青海', '宁夏', '新疆', '台湾', '香港', '澳门']

province_postage = {
    "上海": 0, "江苏": 0, "浙江": 0, "山西": 5, "内蒙古": 5, "辽宁": 5, "吉林": 5, "黑龙江": 5, "北京": 5, 
    "天津": 5, "河北": 5, "安徽": 5, "福建": 5, "江西": 5, "山东": 5, "河南": 5, "湖北": 5, "湖南": 5, 
    "广东": 5, "广西": 5, "海南": 5, "重庆": 5, "四川": 5, "贵州": 5, "云南": 5, "宁夏": 5, "陕西": 5, 
    "甘肃": 10, "青海": 10, "西藏": 10, "新疆": 10, "台湾": 15, "香港": 15, "澳门": 15
}


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
        self.auth = auth.Auth(conf.URL)
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
        
        self.address = random.choice(provinces)          
        self.auth.set_address(self.buyer_id, self.address)
        
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
    
    
    def test_discount(self):
        self.total_count = 0
        for item in self.buy_book_info_list:
            num = item[1]
            self.total_count += num

        if(self.total_count > 3):
            self.total_price *= 0.9
        elif(self.total_count > 5):
            self.total_price *= 0.8
        elif(self.total_count > 10):
            self.total_price *= 0.6
        
        code, res = self.buyer.discount(self.order_id)
        assert code == 200
        assert self.total_price == res['total_price'] 
        
        
    def test_postage(self):
        _postage = 0                                      
        for province, postage in province_postage.items():
            if(province == self.address):
                _postage = postage
        code, res = self.buyer.postage(self.order_id)
        assert _postage == res['postage']
    

    def test_recommend_book(self):                     
        sale_amount = 0
        for _, buy_num in self.buy_book_info_list:
            if(buy_num >= sale_amount):
                sale_amount = buy_num
        
        code, res = self.buyer.recommend(self.store_id, self.order_id)
        
        assert res['sale_amount'] == sale_amount


