import warnings
from itertools import product

import pandas as pd
from pandas.errors import PerformanceWarning


def pivot_table(data, aggfunc, rows=None, columns=None, subtotals=False, subtotal_label='Итог'):
    warnings.simplefilter(action='ignore', category=PerformanceWarning)
    # any loc column selector could be used
    if rows:
        rows = data.loc[:, rows].columns.values.tolist()
        fake_row_used = False
    else:
        # special no_rows case -> creating fake row
        data = data.assign(**{'': [1] * len(data.index.values)})
        rows = ['']
        fake_row_used = True
    num_rows = len(rows)

    # any loc column selector could be used
    if columns:
        columns = data.loc[:, columns].columns.values.tolist()
    else:
        columns = []
    num_cols = len(columns)

    # any loc column selector could be used
    if aggfunc:
        aggfunc = {val: aggfunc[key] for key, val in zip(data.loc[:, [*aggfunc]].columns.values, [*aggfunc])}

    pvt = data.pivot_table(index=rows, columns=columns, values=[*aggfunc], aggfunc=aggfunc, margins=subtotals,
                           margins_name=subtotal_label)

    if not subtotals:
        return pvt

    subpivots = [pvt]

    if num_rows > 0:
        row_prod = [rows[:num_rows_included] for num_rows_included in range(num_rows, 0, -1)]
    else:
        row_prod = [[]]

    if num_cols > 0:
        col_prod = [columns[:num_cols_included] for num_cols_included in range(num_cols, 0, -1)]
    else:
        col_prod = [[]]

    for temp_rows, temp_cols in product(row_prod, col_prod):
        num_rows_included = len(temp_rows)
        num_cols_included = len(temp_cols)

        if num_rows_included == num_rows and num_cols_included == num_cols:
            # original pivot table is already computed!
            continue

        if num_rows_included == 0 and num_cols_included == 1:
            continue

        temp_pvt = data.pivot_table(index=temp_rows, columns=temp_cols, values=[*aggfunc], aggfunc=aggfunc,
                                    margins=True, margins_name=subtotal_label)

        # removing grand total for row and columns, that is computed every time
        temp_pvt.loc[temp_pvt.index.get_level_values(0) == subtotal_label,
                     temp_pvt.columns.get_level_values(0) == subtotal_label] = None

        if num_rows_included != num_rows:
            # removing already computed total
            temp_pvt = temp_pvt.loc[~(temp_pvt.index.get_level_values(0) == subtotal_label), :]

            # making index look ok
            row_content = []
            # subtotal part
            for i in range(num_rows_included):
                level_values = temp_pvt.index.get_level_values(i)
                if i == num_rows_included - 1:
                    level_values = level_values.astype(str) + f' {subtotal_label}'
                row_content.append(level_values)
            # empty part
            for i in range(num_rows_included, len(rows)):
                row_content.append([''] * len(temp_pvt.index.values))
            temp_pvt.index = pd.MultiIndex.from_arrays(row_content)

        if num_cols_included != num_cols:
            # removing already computed total
            temp_pvt = temp_pvt.loc[:, ~(temp_pvt.columns.get_level_values(1) == subtotal_label)]

            # making columns look ok
            col_content = []
            # subtotal part (including aggregates holder)
            for i in range(0, num_cols_included + 1):
                level_values = temp_pvt.columns.get_level_values(i)
                if i == num_cols_included:
                    level_values = level_values.astype(str) + f' {subtotal_label}'
                col_content.append(level_values)
            # empty part
            for i in range(num_cols_included, len(columns)):
                col_content.append([''] * len(temp_pvt.columns.values))
            temp_pvt.columns = pd.MultiIndex.from_arrays(col_content)

        temp_pvt.columns.names = [''] + columns
        temp_pvt.index.names = rows

        subpivots.append(temp_pvt)

    pvt = pd.concat(subpivots, sort=False).reset_index().groupby(rows).sum()[[*aggfunc]].sort_index(axis=1)
    if fake_row_used:
        pvt = pvt.loc[pvt.index != 1, :]

    warnings.simplefilter(action='default', category=PerformanceWarning)
    return pvt


if __name__ == '__main__':
    df = pd.DataFrame({
        'a': [1, 1, 1, 1, 1, 1, 1, 1, 1],
        'b': [1, 1, 1, 2, 2, 2, 3, 3, 3],
        'c': [1, 1, 1, 1, 1, 1, 1, 1, 1],
        'd': [1, 1, 1, 2, 2, 2, 3, 3, 3],
        'e': [1, 2, 3, 4, 5, 6, 7, 8, 9],
    })

    test_cases = {
        '#1: multiple rows + multiple columns': {
            'rows': ['a', 'b'],
            'columns': ['c', 'd'],
            'aggfunc': {'e': 'sum'}
        },
        '#2: multiple rows + single column': {
            'rows': ['a', 'b'],
            'columns': ['c'],
            'aggfunc': {'e': 'sum'}
        },
        '#3: single row + multiple columns': {
            'rows': ['a'],
            'columns': ['c', 'd'],
            'aggfunc': {'e': 'sum'}
        },
        '#4: single row + single column': {
            'rows': ['a'],
            'columns': ['c'],
            'aggfunc': {'e': 'sum'}
        },
        '#5: multiple rows + no columns': {
            'rows': ['a', 'b'],
            'columns': [],
            'aggfunc': {'e': 'sum'}
        },
        '#6: single row + no columns': {
            'rows': ['a'],
            'columns': [],
            'aggfunc': {'e': 'sum'}
        },
        '#7: no rows + multiple columns': {
            'rows': [],
            'columns': ['c', 'd'],
            'aggfunc': {'e': 'sum'}
        },
        '#8: no rows + single column': {
            'rows': [],
            'columns': ['c'],
            'aggfunc': {'e': 'sum'}
        }
    }

    for test_case, conditions in test_cases.items():
        print(test_case)
        print(pivot_table(df, subtotals=True, **conditions))
