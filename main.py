from argparse import ArgumentParser
from time import perf_counter
import grequests
import func
import codecs
import gc
import os
from const import REQUEST_HEADERS, DPS_REPORT_JSON_URL, DEFAULT_LANGUAGE, DEFAULT_TITLE, DEFAULT_INPUT_FILE, ALL_BOSSES, ALL_PLAYERS
from models.log_class import Log
from models.boss_facto import BossFactory
from languages import LANGUES
from input import InputParser
import time
import random
def _make_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', required=False)

    parser.add_argument('-l', '--language', required=False, default=DEFAULT_LANGUAGE)
    parser.add_argument('-r', '--reward', action='store_true', required=False)
    parser.add_argument('-i', '--input', required=False, default=DEFAULT_INPUT_FILE)
    return parser

def debugLog(url):
    log = Log(url)
    jcontent = grequests.get(url)
    pjcontent = grequests.get(DPS_REPORT_JSON_URL, params={"permalink": url}, headers=REQUEST_HEADERS)
    responses = grequests.map([jcontent, pjcontent], size=2)
    log.set_jcontent(responses[0])
    log.set_pjcontent(responses[1])
    BossFactory.create_boss(log)
    boss = ALL_BOSSES[0]
    print(boss.start_date)
    print(boss.mvp)
    print(boss.lvp)
    #ALL_BOSSES.clear()
    #ALL_PLAYERS.clear()

def main(input_file, **kwargs) -> None:
    urls = InputParser(input_file).validate().urls
    
    # Process URLs in batches to reduce memory usage
    # Batch size: configurable via env var, default 5 URLs = 10 requests at a time (fits in 512MB)
    # For very memory-constrained environments, set FLAME_BATCH_SIZE=3 or lower
    BATCH_SIZE = int(os.environ.get("FLAME_BATCH_SIZE", "3"))
    CONCURRENCY = int(os.environ.get("FLAME_CONCURRENCY", "1"))  # Reduced from 4 to limit memory
    
    for batch_start in range(0, len(urls), BATCH_SIZE):
        batch_urls = urls[batch_start:batch_start + BATCH_SIZE]
        requests_list = []

        for url in batch_urls:
            requests_list.append(grequests.get(url))
            requests_list.append(grequests.get(DPS_REPORT_JSON_URL + url, headers=REQUEST_HEADERS))
            time.sleep(random.uniform(0.3, 0.8))  # 300–800ms random delay

        # Process this batch with limited concurrency
        responses = grequests.map(requests_list, size=CONCURRENCY)
        
        # Create logs for this batch only
        batch_logs = [Log(url) for url in batch_urls]
        for i in range(len(batch_urls)):
            batch_logs[i].set_jcontent(responses[2*i])
            batch_logs[i].set_pjcontent(responses[2*i+1])
        
        # Create bosses from this batch (they get added to ALL_BOSSES)
        for log in batch_logs:
            BossFactory.create_boss(log)
        
        # Clear batch data to free memory
        # Note: Boss objects are kept in ALL_BOSSES (they reference Log objects with JSON data)
        # We clear the HTTP response objects which can be large, and force GC
        del responses
        del requests_list
        # batch_logs are referenced by Boss objects, so they won't be GC'd yet
        del batch_logs
        gc.collect()  # Force garbage collection after each batch
        
        print(f"Processed batch {batch_start // BATCH_SIZE + 1}/{(len(urls) + BATCH_SIZE - 1) // BATCH_SIZE}")
    
    print("\n")
    split_run_message = func.get_message_reward(ALL_BOSSES, ALL_PLAYERS, titre=DEFAULT_TITLE)

    # Remove all blanks from the text and print
    for i in range(len(split_run_message)):
        text = split_run_message[i]
        text_out = "".join([s for s in text.strip().splitlines(True) if s.strip()])
        print(text_out)


    # Write to text file
    # Use environment variable if set (for Discord bot concurrent requests), otherwise use default
    output_path = os.environ.get("FLAME_OUTPUT_PATH", "Flame_Output.txt")
    with open(output_path, "w", encoding="utf-8") as f: 
        text_out = ""
        for i in range(len(split_run_message)): 
            text = split_run_message[i]
            while "\n\n" in text and i < 100:
                text = text.replace("\n\n","\n")
            text_out += text
        text_out = text_out.replace("\n\n","\n")
        f.write(text_out)


if __name__ == "__main__":
    print("Starting\n")
    start_time = perf_counter()
    
    # Language selection: 
    #
    # "EN"       : General flame
    # "EN_PMA"   : PMA, notices mechanics but doesn't flame too much.
    # "EN_short" : short and concise, doesn't really flame
    # "FR"       : French, legacy code, doesn't work anymore
    # "DE"       : German, translated by someone who doesn't know German :)
    
    LANGUES["selected_language"] = LANGUES["EN_PMA"]
    
    
    args = _make_parser().parse_args()
    main(args.input, reward_mode=args.reward, debug=args.debug, language=args.language)
    #debugLog("https://dps.report/YUU0-20250518-111201_cairn")
    end_time = perf_counter()
    print(f"--- {end_time - start_time:.3f} seconds ---\n")