import concurrent.futures
from datetime import date
import pandas as pd
from pathlib import Path
import time
from hw1.data.data_storage import DataStorage
from hw1.filters.issuer_filter import IssuerFilter
from hw1.filters.stock_data_scraper import StockDataScraper


class StockDataManager:
    def __init__(self, output_dir="../stock_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.storage = DataStorage()
        self.scraper = StockDataScraper()

    @staticmethod
    def format_price(price):
        if isinstance(price, str) and price != '/':
            price_float = float(price.replace(',', '').replace(' ', ''))
            return f"{price_float:,.2f}".replace(',', ' ').replace('.', ',').replace(' ',
                                                                                     '.')
        return price

    def process_issuer(self, issuer):
        storage_data = self.storage.load_data()
        from_date = storage_data.get(issuer)
        output_file = self.output_dir / f"{issuer}.csv"

        if from_date and output_file.exists():
            existing_df = pd.read_csv(output_file)
            existing_df['datetime_parsed'] = pd.to_datetime(existing_df['datetime_parsed'])
        else:
            existing_df = pd.DataFrame()

        data = self.scraper.scrape_issuer_data(issuer, from_date)
        if data:
            new_df = pd.DataFrame(data)
            new_df['datetime_parsed'] = pd.to_datetime(new_df['Date'], format="%m/%d/%Y")
            new_df['Date'] = new_df['datetime_parsed'].dt.strftime('%d.%m.%Y')

            price_columns = ['Last trade price', 'Max', 'Min', "%chg.", 'Avg. Price',
                             'Turnover in BEST in denars', 'Total turnover in denars']
            for col in price_columns:
                new_df[col] = new_df[col].apply(self.format_price)

            try:
                if not existing_df.empty:
                    combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['Date']).sort_values(
                        by='datetime_parsed')
                else:
                    combined_df = new_df.sort_values(by='datetime_parsed')

                combined_df.to_csv(output_file, index=False)

                self.storage.update_issuer(issuer, date.today().strftime("%m/%d/%Y"))

                print(f"Successfully saved {len(new_df)} new records for {issuer}")
            except Exception as e:
                print(f'Error in saving the data {e}')
        else:
            print(f"No new data collected for {issuer}")

    def process_all_issuers(self, max_workers=8):
        issuers = IssuerFilter.get_all_issuers()

        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.process_issuer, issuers)


def main():
    manager = StockDataManager()
    manager.process_all_issuers()


if __name__ == '__main__':
    start_time = time.time()
    main()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Execution time: {elapsed_time:.2f} seconds")
