import pyperclip

from textwrap import dedent
from unittest import TestCase
from .utils import create_redasql_process, commands_to_str


class CliTest(TestCase):
    """
    need docker
    """

    def setUp(self) -> None:
        self.process = create_redasql_process()

    def tearDown(self) -> None:
        if self.process.returncode is None:
            self.process.kill()

    def test_describe_command__with_no_schema(self):
        stdout, stderr = self.process.communicate('\\d\n'.encode())
        stdout = stdout.decode('utf-8')
        expected = dedent("""\
        - city
        - country
        - countrylanguage
        """)
        self.assertIn(expected, stdout)

    def test_describe_command__with_schema(self):
        commands = [
            '\\d city',
        ]
        stdout, stderr = self.process.communicate(commands_to_str(commands).encode())
        stdout = stdout.decode('utf-8')
        expected = dedent("""\
        ## city
        - ID
        - Name
        - CountryCode
        - District
        - Population
        """)
        # v8, v9 order different.
        for line in expected.splitlines():
            self.assertIn(line, stdout)

    def test_execute_query(self):
        sql = 'select Code, Name from country order by Code limit 3;'
        stdout, stderr = self.process.communicate(f'{sql}\n'.encode())
        stdout = stdout.decode('utf-8')
        expected = dedent("""\
        +--------+-------------+
        | Code   | Name        |
        |--------+-------------|
        | ABW    | Aruba       |
        | AFG    | Afghanistan |
        | AGO    | Angola      |
        +--------+-------------+
        
        3 rows returned.
        """)
        self.assertIn(expected, stdout)
        self.assertIn('', stdout)

    def test_execute_query_pivoted_table(self):
        sql = 'select Code, Name from country order by Code limit 3;'
        commands = [
            '\\x',
            sql
        ]
        stdout, stderr = self.process.communicate(commands_to_str(commands).encode())
        stdout = stdout.decode('utf-8')
        expected = dedent("""\
        -[RECORD 1]----
        Code| ABW
        Name| Aruba
        -[RECORD 2]----
        Code| AFG
        Name| Afghanistan
        -[RECORD 3]----
        Code| AGO
        Name| Angola
        
        
        3 rows returned.
        """)
        self.assertIn(expected, stdout)
        self.assertIn('', stdout)

    def test_execute_query_markdown(self):
        sql = 'select Code, Name from country order by Code limit 3;'
        commands = [
            '\\f markdown',
            sql
        ]
        stdout, stderr = self.process.communicate(commands_to_str(commands).encode())
        stdout = stdout.decode('utf-8')
        expected = dedent("""\
        | Code   | Name        |
        |--------|-------------|
        | ABW    | Aruba       |
        | AFG    | Afghanistan |
        | AGO    | Angola      |
        
        3 rows returned.
        """)
        self.assertIn(expected, stdout)
        self.assertIn('', stdout)

    def test_execute_query_markdown_with_sql(self):
        sql = 'select Code, Name from country order by Code limit 3;'
        commands = [
            '\\f markdown_with_sql',
            sql
        ]
        stdout, stderr = self.process.communicate(commands_to_str(commands).encode())
        stdout = stdout.decode('utf-8')
        expected = dedent("""\
        ```sql
        select Code, Name from country order by Code limit 3;
        ```
        
        | Code   | Name        |
        |--------|-------------|
        | ABW    | Aruba       |
        | AFG    | Afghanistan |
        | AGO    | Angola      |
        
        3 rows returned.
        """)
        self.assertIn(expected, stdout)
        self.assertIn('', stdout)

    def test_execute_query_copy_query_result_to_clipboard(self):
        sql = 'select Code, Name from country order by Code limit 3;'
        commands = [
            '\\cp',
            sql
        ]
        stdout, stderr = self.process.communicate(commands_to_str(commands).encode())
        stdout = stdout.decode('utf-8')
        expected = dedent("""\
        +--------+-------------+
        | Code   | Name        |
        |--------+-------------|
        | ABW    | Aruba       |
        | AFG    | Afghanistan |
        | AGO    | Angola      |
        +--------+-------------+
        """)
        self.assertIn(expected, stdout)
        self.assertIn('', stdout)
        self.assertIn(expected, pyperclip.paste())
