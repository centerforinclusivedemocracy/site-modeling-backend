# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 15:40:18 2019

@author: Gorgonio

Created based on DK's Postgis Pandas package, for interacting with Postgres/Postgis and Python Pandas
"""
from sqlalchemy import * #TODO: Confirm if any other imports other than create_engine are needed
import pandas as pd

private = {}
class postgis_pandas(object):
    #TODO: Update description
    """ 
    """
    #TODO: Re-include app_paths=app_paths if needed
    def __init__(self, db_params, do_echo=True):

        private[self,'dbhost'] = db_params.get("host")
        private[self,'dbuser'] = db_params.get("user")
        private[self,'dbpwd']  = db_params.get("pwd")

        self.dbname = db_params.get("dbname")
        self.dbport = db_params.get("port")
        self.pwd_cmd="export PGPASSWORD=" + '"' + private[self,'dbpwd'] + '"'
        #self.app_paths = app_paths
        
        cmd = f"postgresql://{private[self,'dbuser']}:" + \
            f"{private[self,'dbpwd']}@{private[self,'dbhost']}:{self.dbport}/{self.dbname}" 
        self.engine = create_engine(cmd, echo = do_echo, encoding='utf-8')

        # Close a preexisting connection (if instantiating a new instance)
        print('Closing existing connection if one exists')
        try:
            self.con.close()
        except:
            print('No existing connection to close')

        # Open a new connection
        print('Opening new connection')
        try:
            self.con = self.engine.connect()
            print("Python<-->DB Connection Succeeded")
        except:
            print("Python<-->DB Connection Failed")
    
    def qry(self, q):
        return self.con.execute(text(q))
    
    # Used 4-5 times in CCEP1    
    def add_column(self, schema, table, column_name, column_type):
        try:
            self.qry(f"""ALTER TABLE {schema}.{table} ADD COLUMN {column_name} {column_type};""")
            print(f"... add column {column_name} succeeded")
        except:
            print(f"... add column {column_name} failed")            
            
    # Copy from col2 to col1 where joinid_1 = joinid_2
    # ... col1 has to exist, and the 2 col datatypes have to match
    # Used 4-5 times in CCEP1    
    def column_copy(self, schema_1, table_1, col_1, joinid_1, schema_2, table_2, col_2, joinid_2):
        qry_txt = f"""UPDATE {schema_1}.{table_1} 
            AS a 
            SET {col_1} = b.{col_2} 
            FROM {schema_2}.{table_2} 
            AS b 
            where a.{joinid_1}=b.{joinid_2};
            """
        self.qry(qry_txt)
    
    # Used only twice, both times in CCEP1
    def intersect(self, output_schema_name, input_schema_name1, id_1, label_1, \
                  input_schema_name2, id_2, label_2):
        output_schema = output_schema_name.split('.')[0]
        a_schema = input_schema_name1.split('.')[0]
        b_schema = input_schema_name2.split('.')[0]
        qry_txt = f"""	
            DROP INDEX IF EXISTS {a_schema}.a_gdx;
    		DROP INDEX IF EXISTS {b_schema}.b_gdx;
    		CREATE INDEX a_gdx ON {input_schema_name1}  USING GIST(geom);
    		CREATE INDEX b_gdx ON {input_schema_name2} USING GIST(geom);

    		CREATE TABLE {output_schema_name} AS 
    		SELECT
    		  a.{id_1} AS {label_1}_gid,
    		  b.{id_2} AS {label_2}_gid,
    		  CASE 
    		     WHEN ST_Within(a.geom,b.geom) 
    		     THEN a.geom
    		     ELSE ST_Multi(ST_Intersection(a.geom,b.geom)) 
    		  END AS geom
    		FROM {input_schema_name1}  a
    		JOIN {input_schema_name2} AS b
    		ON ST_Intersects(a.geom, b.geom)
            """
        self.qry(qry_txt)

        # TODO: This wasn't used, is it needed? Commented until we confirm
        # cleanup = """drop index {}.a_gdx, {}.b_gdx;"""
        
        #TODO: Check if this is needed, doesn't appear to be
        #if return_df:
        #	return self.table2df(output_schema, output_schema_name.split('.')[1])
    # End intersect()

    # Used in multiple CCEP files
    def table2df(self, schema, table):
        tempcon =  self.qry(f"""select * from {schema}.{table}""")
        df = pd.DataFrame(tempcon.fetchall(), columns = tempcon.keys())
        tempcon.close()
        return df

    # Used once each in CCEP1 and CCEP3
    def df2table(self, df, schema, newname, append=False, create_index=False):
        """
        df: the df that you want to upload to the db
        schema: destination schema
        newname: name of the table
        append: if inserting rows into an existing table set append = True
        create_index: If you want an index to be created in postgres table set to TRUE - useful if one does not yet exist
        """
        if append:
            df.to_sql(name=newname, schema=schema, con=self.engine, chunksize=100000, index=create_index, if_exists='append')
        else:
            df.to_sql(name=newname, schema=schema, con=self.engine, chunksize=100000, index=create_index)

        if 'geom' in df.columns:
            try:
                self.convert_column2geom(schema=schema, table_name=newname, column_name='geom')
            except:
                print('... no geom column exists, or geometry column not named geom.')

    # Added for manual debugging and error handling
    def see_all_processes(self):
        out = self.qry("""select datid,datname, pid,usename,application_name,query_start,state,query from pg_stat_activity""").fetchall()
        print(out)
        print(pd.DataFrame(out,columns = ['datid','datname', 'pid','usename','application_name','query_start','state','query']))

    # Added for manual debugging and error handling. Not tested.
    def kill_process(self, pid):
        self.qry(f"""select pg_cancel_backend({format(pid)})""").close()