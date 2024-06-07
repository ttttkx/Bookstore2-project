import threading
from datetime import datetime, timedelta
from be.model import error, db_conn
from be.model.store import NewOrder


class OrderAutoCancel(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)
        self.cancel_timer = threading.Timer(60, self.cancel_unpaid_orders)  # 定时器每分钟执行一次
        self.cancel_timer.start()

    def cancel_unpaid_orders(self):
        try:
            current_time = datetime.now()
            time_interval = current_time - timedelta(minutes=1)

            unpaid_order_cursor = self.conn.query(NewOrder).filter_by(status = "unpaid").all()
            for order in unpaid_order_cursor:
                order_time = datetime.fromisoformat(str(order.created_at))
                if order_time < time_interval:
                    order.status = "cancelled"
            self.conn.commit()
        except Exception as e:
            print(f"Error canceling unpaid orders: {str(e)}")

        # 重新启动定时器
        self.cancel_timer = threading.Timer(60, self.cancel_unpaid_orders)
        self.cancel_timer.start()


if __name__ == "__main__":
    order_auto_cancel = OrderAutoCancel()
