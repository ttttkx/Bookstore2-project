import pymongo
import uuid
import json
import logging
from be.model import error
from be.model import db_conn
from sqlalchemy import create_engine, text 
import base64
from be.model.store import NewOrder, NewOrderDetail, User as UserModel, Store as StoreModel, Book as BookModel

class Book(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)


    def search_in_store(self, store_id, title, author, publisher, isbn, content, tags, book_intro, page=1, per_page=10):
        try:
            # 获取 store_id 对应的所有书籍 ID
            store_books = self.conn.query(StoreModel.book_id).filter_by(store_id=store_id).all()
            book_ids = [book_id for book_id, in store_books]

            # 构建查询条件
            query_conditions = []
            if title:
                query_conditions.append(BookModel.title.like(f"%{title}%"))
            if author:
                query_conditions.append(BookModel.author.like(f"%{author}%"))
            if publisher:
                query_conditions.append(BookModel.publisher.like(f"%{publisher}%"))
            if isbn:
                query_conditions.append(BookModel.isbn.like(f"%{isbn}%"))
            if content:
                query_conditions.append(BookModel.content.like(f"%{content}%"))
            if tags:
                query_conditions.append(BookModel.tags.like(f"%{tags}%"))
            if book_intro:
                query_conditions.append(BookModel.book_intro.like(f"%{book_intro}%"))
            # 计算分页参数
            offset = (page - 1) * per_page
            # 构建完整的查询
            books_query = self.conn.query(BookModel).filter(
                BookModel.id.in_(book_ids),
                *query_conditions
            )

            books = books_query.offset(offset).limit(per_page).all()
            result = []
            for book in books:
                result.append({"id":book.id})

        except Exception as e:
            return 528, "{}".format(str(e))

        return 200, result

    def search_all(self, title, author, publisher, isbn, content, tags, book_intro, page=1, per_page=10):
        try:
            qs_dict = {
                'title': title,
                'author': author,
                'publisher': publisher,
                'isbn': isbn,
                'content': content,
                'tags': tags,
                'book_intro': book_intro
            }
            qs_dict1 = {key: value for key, value in qs_dict.items() if value}

            # 构建查询条件
            query_conditions = []
            for key, value in qs_dict1.items():
                query_conditions.append(getattr(BookModel, key).like(f"%{value}%"))

            # 构建完整的查询
            books_query = self.conn.query(BookModel).filter(*query_conditions)
            # 计算分页参数
            offset = (page - 1) * per_page

            # 执行查询，并限制结果数量
            books = books_query.offset(offset).limit(per_page).all()

            result = []
            for book in books:  
                result.append({"id":book.id})

        except Exception as e:
            return 528, "{}".format(str(e))
        return 200, result
