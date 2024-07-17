import logging

def setup_logger( *, lv=None, log_dir:str|None = None ):
    import os,sys
    from datetime import datetime

    if lv is None:
        lv = logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # ロガーのログレベルを設定

    # コンソール出力用のハンドラを作成
    console_handler = logging.StreamHandler()
    console_handler.setLevel(lv)  # コンソールにはINFO以上のログを出力
    # ログメッセージのフォーマットを設定
    formatter2 = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    console_handler.setFormatter(formatter2)

    # ハンドラをロガーに追加
    root_logger.addHandler(console_handler)

    if log_dir:
        # 現在の日時を取得し、ファイル名に適した形式にフォーマット
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = os.path.join( log_dir,f'test_voice_{current_time}.log')
        os.makedirs( log_dir, exist_ok=True )
        # ファイル出力用のハンドラを作成
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)  # ファイルにはERROR以上のログを記録
        # ログメッセージのフォーマットを設定
        formatter1 = logging.Formatter('%(asctime)s %(module)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter1)
        # ハンドラをロガーに追加
        root_logger.addHandler(file_handler)
