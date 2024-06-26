import sys
import os
sys.path.append(os.getcwd())
import LocalInterpreter.utils.trends as trends

def test_today_trends_search():
    text:str = trends.today_searches_result()
    print(f"{text}")

def main():
    from dotenv import load_dotenv, find_dotenv
    load_dotenv( find_dotenv('.env_google') )
    
    test_today_trends_search()

if __name__ == "__main__":
    main()