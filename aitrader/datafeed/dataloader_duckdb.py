from datetime import datetime

import duckdb
import pandas as pd
from tqdm import tqdm


class DuckdbLoader:
    def __init__(self, path, symbols, cols=['close'], start_date='20100101',
                 end_date=datetime.now().strftime('%Y%m%d'), folder='/*'):
        self.path = path
        self.folder = folder
        self.start_date = start_date
        self.end_date = end_date
        self.cols = cols
        self.symbols = symbols
        self.df = None
        self._load_data(self.symbols, self.cols)

    def get_col_df(self, col='close'):
        if col not in self.df.columns:
            print('列数据没有加载！')
            return None

        df_col = self.df[[col, 'symbol']].pivot_table(values=col, index=self.df.index, columns='symbol')
        return df_col

    def _load_data(self, symbols, columns):
        columns.extend(['symbol', 'date'])
        cols_str = ','.join(columns)

        symbols_str = None
        if symbols and len(symbols):
            symbols = ["'{}'".format(s) for s in symbols]
            symbols_str = ",".join(symbols)

        query_str = """
    select {} from '{}{}/*.csv'
    where date >= '{}' and date <= '{}'
    """.format(cols_str, self.path, self.folder, self.start_date, self.end_date)
        if symbols_str:
            query_str += ' and symbol IN ({})'.format(symbols_str)

        df = duckdb.query(
            query_str
        ).df()
        df['date'] = df['date'].apply(lambda x: str(x))
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True, ascending=True)
        self.df = df

    def calc_all_expressions(self, fields, names):
        df = self.df
        cols = []
        count = 0
        df.set_index([df.index, 'symbol'], inplace=True)
        for field, name in tqdm(zip(fields, names)):
            try:
                if len(field) <= 0:
                    continue
                se = calc_expr(df, field)

                count += 1
                if count < 10:
                    df[name] = se
                else:
                    se.name = name
                    cols.append(se)
            except:
                print('{}错误'.format(field))
                import traceback
                print(traceback.print_exc())
                continue
        if len(cols):
            df_cols = pd.concat(cols, axis=1)
            df = pd.concat([df, df_cols], axis=1)

        # df_all = df.loc[self.start_date: self.end_date].copy()
        # print(df_all.index.levels[0])
        df['symbol'] = df.index.droplevel(0)
        # df_all['symbol'] = df_all.index.levels[0]
        df.index = df.index.droplevel(1)
        self.df = df


if __name__ == '__main__':
    from configs import DATA_ETF_QUOTES

    loader = DuckdbLoader(path=DATA_ETF_QUOTES.resolve(), symbols=['510300.SH', '159915.SZ'],
                          cols=['close', 'adj_factor'])
    df_col = loader.get_col_df('adj_factor')
    print(df_col)

    from datafeed.expr import calc_expr

    loader.calc_all_expressions(fields=['roc(close,20)'], names=['roc_20'])
    df = loader.get_col_df('roc_20')
    print(df)
