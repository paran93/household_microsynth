
# Household projection

import io
import os
import datetime
from dateutil.relativedelta import relativedelta
from urllib import request
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from socket import timeout
import pandas as pd


def get_postcode_lookup(filename):
  return pd.read_csv(filename)

# Example URL for downloading new build sales
# http://landregistry.data.gov.uk/app/ppd/ppd_data.csv?et%5B%5D=lrcommon%3Afreehold&et%5B%5D=lrcommon%3Aleasehold&header=true&limit=all&max_date=31+July+2016&min_date=1+July+2016&nb%5B%5D=true&ptype%5B%5D=lrcommon%3Adetached&ptype%5B%5D=lrcommon%3Asemi-detached&ptype%5B%5D=lrcommon%3Aterraced&ptype%5B%5D=lrcommon%3Aflat-maisonette&tc%5B%5D=ppd%3AstandardPricePaidTransaction&tc%5B%5D=ppd%3AadditionalPricePaidTransaction
def get_newbuilds(month, year):

  start_date = datetime.date(year,month,1)
  end_date = start_date + relativedelta(months=1, days=-1)

  url = "http://landregistry.data.gov.uk/app/ppd/ppd_data.csv?et%5B%5D=lrcommon%3Afreehold&et%5B%5D=lrcommon%3Aleasehold&header=true&limit=all&max_date=" \
      + end_date.strftime("%d+%B+%Y") + "&min_date=" + start_date.strftime("%d+%B+%Y") \
      + "&nb%5B%5D=true&ptype%5B%5D=lrcommon%3Adetached&ptype%5B%5D=lrcommon%3Asemi-detached&ptype%5B%5D=lrcommon%3Aterraced" \
      + "&ptype%5B%5D=lrcommon%3Aflat-maisonette&tc%5B%5D=ppd%3AstandardPricePaidTransaction&tc%5B%5D=ppd%3AadditionalPricePaidTransaction"

  # check cache for previously downloaded data
  rawdata_file = "./data/raw" + start_date.isoformat() + "_" + end_date.isoformat() + ".csv"
  if os.path.isfile(rawdata_file):
    print("using local data: " + rawdata_file)
    newbuild_data = pd.read_csv(rawdata_file)
  else:
    print("downloading data to: " + rawdata_file)
    try:
      response = request.urlopen(url)
    except (HTTPError, URLError, timeout) as error:
      print('ERROR: ', error, ' accessing', url)
      return

    newbuild_data = pd.read_csv(io.StringIO(response.read().decode('utf-8')))
    newbuild_data = newbuild_data.fillna('')

    newbuild_data.to_csv(rawdata_file)

  return newbuild_data

def batch_newbuilds(start_year, end_year):

  pcdb = get_postcode_lookup("./data/postcode_oa_lookup_201708.csv")

  # map build type to census codes (see e.g. LC4402EW)
  buildtype_lookup = { "D": "2", "S": "3", "T": "4", "F": "5" }
  
  # inclusive range
  for y in range(start_year, end_year+1):
    for m in range(1, 13):

      output_file = "./data/newbuilds_" + str(y) + format(m, "02") + ".csv"
      if os.path.isfile(output_file):
        print("File exists: " + output_file + ", skipping")
        continue

      newbuilds = get_newbuilds(m, y)
      # use this for debugging
      #newbuilds = pd.read_csv("~/newbuilds_test.csv")
      # empty values are empty strings, not (the default) NaN
      #print(newbuilds.head())

      output = { }

      print(str(y) + "/" + str(m) + ": " + str(len(newbuilds.index)) + " new sales")
      for i in range(0, len(newbuilds.index)):
        postcode = newbuilds.at[i,"postcode"]
        pc_match = pcdb.ix[pcdb.Postcode == postcode]

        if len(pc_match) > 1:
          print("Multiple entries found for postcode " + str(postcode))
          continue
        elif len(pc_match) == 0:
          print("Zero entries found for postcode " + str(postcode))
          # use postcode district if available to at least get LAD?
          area_code = "UNKNOWN"
        else:
          area_code = pc_match["OA11"].iloc[0]

        build_type = buildtype_lookup[newbuilds.at[i, "property_type"]]
        if not(area_code in output):
          output[area_code] = { build_type : 1 }
        elif not(build_type in output[area_code]):
          output[area_code][build_type] = 1 
        else:
          output[area_code][build_type] += 1 
      output_df = pd.DataFrame.from_dict(output, orient="index",dtype="int64")
      output_df = output_df.fillna(int(0))
      output_df = output_df.astype(int)
      #print(output_df.head())
      output_df.to_csv(output_file)  


