import os,sys,time,traceback
from datetime import datetime
import bisect
import logging
import json

def setup_logger( *, lv=None, log_dir:str|None = None ):
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

class ApiLog:
    _logger: logging.Logger = None
    
    @staticmethod
    def setup(log_dir):
        if not os.path.isdir(log_dir):
            raise ValueError(f"Invalid log directory: {log_dir}")
        
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = os.path.join(log_dir, f'api_{current_time}.log')
        
        # ファイル出力用のハンドラを作成
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        
        # ログメッセージのフォーマットを設定
        formatter = logging.Formatter('%(asctime)s\n%(message)s\n')
        file_handler.setFormatter(formatter)
        
        # ロガーを取得し、設定
        logger = logging.getLogger('apilog')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
                
        # ロガーの伝播を無効にする
        logger.propagate = False

        # コンソール出力用のハンドラ（必要に応じて）
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.INFO)
        # console_handler.setFormatter(formatter)
        # logger.addHandler(console_handler)
        
        ApiLog._logger = logger

    @staticmethod
    def _to_str( o1 ):
        if isinstance( o1, Exception ):
            return ''.join(traceback.format_exception(type(o1), o1, o1.__traceback__))
        else:
            try:
                return json.dumps(o1, ensure_ascii=False)
            except:
                return str(o1)
            
    @staticmethod
    def log(input, out1, out2=None):
        try:
            if ApiLog._logger is not None:
                input_text = json.dumps(input, ensure_ascii=False)
                txt1 = ApiLog._to_str(out1)
                if out2 is None:
                    msg = f"in:{input_text}\nout:{txt1}"
                else:
                    txt2 = ApiLog._to_str(out2)
                    msg = f"in:{input_text}\nout:{txt1}\n{txt2}"
                if isinstance(out1,Exception) or isinstance(out2,Exception):
                    ApiLog._logger.error( msg )
                else:
                    ApiLog._logger.info( msg )
        except:
            traceback.print_exc()

def delete_old_files(directory, max_size):
    """ディレクトリ内のファイルが指定サイズを超えた場合、作成日が古い順に削除"""
    logger = logging.getLogger('file_cleanup')
    total_size = 0  # 初期化
    max_files = 1000  # ファイルリストの最大サイズ

    # ソートされた状態でファイル情報を保持するリスト
    files = []

    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    creation_time = os.path.getctime(filepath)
                    size = os.path.getsize(filepath)
                    total_size += size

                    # リストがmax_filesのサイズに達している場合、判定してスキップ
                    if len(files) >= max_files:
                        if creation_time >= files[-1][0]:  # 新しいファイルが最も新しい場合スキップ
                            continue
                    
                    # 挿入位置を決定し、ソートされたリストに挿入
                    bisect.insort(files, (creation_time, filepath, size))
                    
                    # filesリストのサイズがmax_filesを超える場合、最も新しいファイルを削除
                    if len(files) > max_files:
                        files.pop()
                        
                except Exception as e:
                    logger.error(f"Error accessing {filepath}: {e}")

    except Exception as e:
        logger.error(f"Error accessing {directory}: {e}")

    if total_size <= max_size:
        return

    # 作成日が古い順にソートされたリスト files からファイルを削除して容量を減らす
    logger.info(f"total {total_size}(bytes) dir:{directory}")
    for creation_time, filepath, filesize in files:
        if total_size <= max_size:
            break
        try:
            os.remove(filepath)
            total_size -= filesize
            logger.info(f"deleted: {filesize} bytes {filepath}")
        except Exception as e:
            logger.error(f"Error deleting {filepath}: {e}")