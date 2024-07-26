
import sys,os
sys.path.append(os.getcwd())
import LocalInterpreter.utils.lxml_util as Xu

table_html_01:str= """
<table>
<tr>
<th>日付</th><td colspan="24">今日 2024年07月18日(木)[赤口]</td>
</tr>

<tr>
<th colspan="2">時刻</th><td colspan="3">未明</td><td colspan="3">明け方</td><td colspan="3">朝</td><td colspan="3">昼前</td><td colspan="3">昼過ぎ</td><td colspan="3">夕方</td><td colspan="3">夜のはじめ頃</td><td colspan="3">夜遅く</td>
</tr>

<tr>
<td>01</td><td>02</td><td>03</td><td>04</td><td>05</td><td>06</td><td>07</td><td>08</td><td>09</td><td>10</td><td>11</td><td>12</td><td>13</td><td>14</td><td>15</td><td>16</td><td>17</td><td>18</td><td>19</td><td>20</td><td>21</td><td>22</td><td>23</td><td>24</td>
</tr>

<tr>
<th>天気</th><td>曇り</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>晴れ</td><td>曇り</td><td>曇り</td><td>晴れ</td><td>小雨</td><td>晴れ</td><td>晴れ</td><td>曇り</td><td>曇り</td>
</tr>

<tr>
<th colspan="2">気温
(℃)</th>
</tr>

<tr>
<td>26.0</td><td>26.5</td><td>25.7</td><td>25.2</td><td>24.9</td><td>25.3</td><td>26.6</td><td>28.0</td><td>29.5</td><td>31.3</td><td>32.3</td><td>33.1</td><td>34.7</td><td>35.2</td><td>34.8</td><td>33.1</td><td>32.3</td><td>31.2</td><td>30.1</td><td>29.0</td><td>28.2</td><td>27.9</td><td>27.6</td><td>27.5</td>
</tr>

<tr>
<th>降水確率</th><td>10</td><td>10</td><td>10</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>20</td><td>20</td><td>0</td><td>50</td><td>10</td><td>10</td><td>20</td><td>20</td>
</tr>

<tr>
<th colspan="2">降水量
(mm/h)</th>
</tr>

<tr>
<td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
</tr>

<tr>
<th>湿度</th><td>96</td><td>97</td><td>95</td><td>95</td><td>96</td><td>94</td><td>90</td><td>83</td><td>75</td><td>66</td><td>61</td><td>58</td><td>56</td><td>54</td><td>53</td><td>53</td><td>56</td><td>59</td><td>64</td><td>70</td><td>75</td><td>78</td><td>80</td><td>82</td>
</tr>

<tr>
<th colspan="2">風向
風速
(m/s)</th><td>南東</td><td>東南東</td><td>東</td><td>東北東</td><td>東</td><td>東</td><td>南東</td><td>南南西</td><td>南西</td><td>南西</td><td>南西</td><td>南西</td><td>西南西</td><td>西南西</td><td>西南西</td><td>西南西</td><td>西南西</td><td>西南西</td><td>西南西</td><td>西南西</td><td>西南西</td><td>南西</td><td>南西</td><td>南西</td>
</tr>

<tr>
<td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>1</td><td>2</td><td>3</td><td>3</td><td>3</td><td>4</td><td>4</td><td>3</td><td>3</td><td>4</td><td>3</td><td>3</td><td>2</td><td>2</td><td>2</td><td>2</td>
</tr>
</table>
"""

import lxml.html

def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}\nActual:\n{actual}\nExpected:\n{expected}")

def test_class():
    # rowspan,colspan無しのテストケース
    table0 = Xu.HtmlTableData()
    table0.tr()
    table0.add("H1", th=True)
    table0.add("H2", th=True)
    table0.add("H3", th=True)
    table0.tr()
    table0.add("R1C1")
    table0.add("R1\nC2")
    table0.add("R1C3")
    table0.tr()
    table0.add("R2C1")
    table0.add("R2C2")
    table0.add("R2C3")
    table0.tr()
    table0.add("R3C1")
    table0.add("R3C2")
    table0.add("R3C3")

    expected0 = (
        "|H1|H2|H3|\n"
        "|---|---|---|\n"
        "|R1C1|R1\\nC2|R1C3|\n"
        "|R2C1|R2C2|R2C3|\n"
        "|R3C1|R3C2|R3C3|"
    )
    result0 = table0.to_markdown()
    print(result0)
    assert_equal(result0, expected0, "Test case basic")

    # rowspan=2のテストケース
    table1 = Xu.HtmlTableData()
    table1.tr()
    table1.add("H1", th=True)
    table1.add("H2", th=True)
    table1.tr()
    table1.add("R1C1 (Rowspan 2)", rows=2)
    table1.add("R1C2")
    table1.tr()
    table1.add("R2C2")
    table1.tr()
    table1.add("R3C1")
    table1.add("R3C2")

    expected1 = (
        "|H1|H2|\n"
        "|---|---|\n"
        "|R1C1 (Rowspan 2)|R1C2|\n"
        "|R1C1 (Rowspan 2)|R2C2|\n"
        "|R3C1|R3C2|"
    )
    result1=table1.to_markdown()
    print(result1)
    assert_equal(result1, expected1, "Test case for rowspan=2 failed")

    # rowspan=5のテストケース
    table2 = Xu.HtmlTableData()
    table2.tr()
    table2.add("H1", th=True)
    table2.add("H2", th=True)
    table2.tr()
    table2.add("R1C1 (Rowspan 5)", rows=5)
    table2.add("R1C2")
    for i in range(4):
        table2.tr()
        table2.add(f"R{i + 2}C2")

    expected2 = (
        "|H1|H2|\n"
        "|---|---|\n"
        "|R1C1 (Rowspan 5)|R1C2|\n"
        "|R1C1 (Rowspan 5)|R2C2|\n"
        "|R1C1 (Rowspan 5)|R3C2|\n"
        "|R1C1 (Rowspan 5)|R4C2|\n"
        "|R1C1 (Rowspan 5)|R5C2|"
    )
    result2=table2.to_markdown()
    print(result2)
    assert_equal(result2, expected2, "Test case for rowspan=5 failed")

    # colspan=2のテストケース
    table3 = Xu.HtmlTableData()
    table3.tr()
    table3.add("H1", th=True)
    table3.add("H2", th=True)
    table3.tr()
    table3.add("R1C1", cols=2)
    table3.tr()
    table3.add("R2C1")
    table3.add("R2C2")

    expected3 = (
        "|H1|H2|\n"
        "|---|---|\n"
        "|R1C1|R1C1|\n"
        "|R2C1|R2C2|"
    )
    result3=table3.to_markdown()
    print(result3)
    assert_equal(result3, expected3, "Test case for colspan=2 failed")

    # colspan=5のテストケース
    table4 = Xu.HtmlTableData()
    table4.tr()
    table4.add("H1", th=True)
    table4.add("H2", th=True)
    table4.tr()
    table4.add("R1C1", cols=5)
    for i in range(5):
        table4.tr()
        table4.add(f"R{i + 2}C1")
        table4.add(f"R{i + 2}C2")

    expected4 = (
        "|H1|H2||||\n"
        "|---|---|---|---|---|\n"
        "|R1C1|R1C1|R1C1|R1C1|R1C1|\n"
        "|R2C1|R2C2|\n"
        "|R3C1|R3C2|\n"
        "|R4C1|R4C2|\n"
        "|R5C1|R5C2|\n"
        "|R6C1|R6C2|"
    )
    result4=table4.to_markdown()
    print(result4)
    assert_equal(result4, expected4, "Test case for colspan=5 failed")

    # rowspanとcolspanを組み合わせたテストケース
    table5 = Xu.HtmlTableData()
    table5.tr()
    table5.add("H1", th=True)
    table5.add("H2", th=True)
    table5.add("H3", th=True)
    table5.tr()
    table5.add("R1C1 (Rowspan 2, Colspan 2)", rows=2, cols=2)
    table5.add("R1C3")
    table5.tr()
    table5.add("R2C3")
    table5.tr()
    table5.add("R3C1")
    table5.add("R3C2")
    table5.add("R3C3")

    expected5 = (
        "|H1|H2|H3|\n"
        "|---|---|---|\n"
        "|R1C1 (Rowspan 2, Colspan 2)|R1C1 (Rowspan 2, Colspan 2)|R1C3|\n"
        "|R1C1 (Rowspan 2, Colspan 2)|R1C1 (Rowspan 2, Colspan 2)|R2C3|\n"
        "|R3C1|R3C2|R3C3|"
    )
    result5=table5.to_markdown()
    print(result5)
    assert_equal(result5, expected5, "Test case for rowspan and colspan failed")


def parse_html_table_lxml(table_html):
    tree = lxml.html.fromstring(table_html)
    table = tree.xpath('//table')[0]

    # Create a list of lists to represent the rows and columns
    rows = table.xpath('.//tr')
    row_data = []

    for row in rows:
        cells = row.xpath('.//td | .//th')
        row_data.append(cells)

    # Calculate the maximum number of columns needed
    max_cols = 0
    for row in row_data:
        col_count = 0
        for cell in row:
            col_count += int(cell.get('colspan', 1))
        if col_count > max_cols:
            max_cols = col_count

    # Create a matrix to hold the table data
    table_matrix = [['' for _ in range(max_cols)] for _ in range(len(row_data))]

    for row_index, row in enumerate(row_data):
        col_index = 0
        for cell in row:
            while table_matrix[row_index][col_index]:
                col_index += 1

            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            cell_text = cell.text_content().strip()

            for i in range(rowspan):
                for j in range(colspan):
                    table_matrix[row_index + i][col_index + j] = cell_text

            col_index += colspan

    return table_matrix

def convert_table_to_markdown(table_matrix):
    markdown_table = []
    for row in table_matrix:
        markdown_row = '| ' + ' | '.join(row) + ' |'
        markdown_table.append(markdown_row)

    # Create the header separator
    header_separator = '| ' + ' | '.join(['---'] * len(table_matrix[0])) + ' |'
    markdown_table.insert(1, header_separator)

    return '\n'.join(markdown_table)

def main():
    # Parse the HTML table
    table_matrix = parse_html_table_lxml(table_html_01)

    # Convert the parsed table to Markdown
    markdown_table = convert_table_to_markdown(table_matrix)
    print(markdown_table)

    with open('tmp/table.md','w') as stream:
        stream.write(markdown_table)


if __name__ == "__main__":
    test_class()
    #main()