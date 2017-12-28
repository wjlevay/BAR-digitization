#!/bin/sh

# FRONTPAGE - Given a collection, goes in and starts snuggling them,
# setting the LEAF in the .xml of the item to be page 0 instead of
# anything else (or nothing at all).

# If there is a filename with the first argument, it will use that file
# for the item list, instead of generating one from the collection.

# Did you even give us an argument; you're killing me Smalls

if [ ! "$1" ]
   then
   echo "No collection name or existing item list given. Please give a collection name or filename."
   exit 1
fi

# Is it a filename or is it a collection?

if [ -f "$1" ]
   then
   echo "Using file $1 for item list to do work."
   sort -u "${1}" > "${1}.txt"
   else
   echo "Grabbing collection list for $1...."
   MET=`ia metadata "$1" | grep '"mediatype": "collection",'`
   if [ "$MET" ]
      then
      echo "Generating an item list for $1...."
      rm -f "${1}.txt"
      ia search --itemlist "collection:${1}" | sort -u > ${1}.txt
      else
      echo "It does not appear this is actually a collection."
      exit 1
   fi
fi
      
# Now you have a file that uses the argument and makes a sorted *.txt file of items.
# Bring the noise - go through all the items in the list.

for book in `cat ${1}.txt`
    do
    echo "========== $book ========="

# New crap I made up: If "coverleaf" is set, don't waste time, we're good.

COVER=`ia metadata $book | grep '"coverleaf"'`
 
if [ "$COVER" ]
   then
   echo "Cover already set. Skipping."
  
  else
    
    SCAND=`ia list ${book} | grep _scandata.xml | head -1`
         if [ "$SCAND" ]
            then
            ia download "${book}" "$SCAND"
            echo "$SCAND downloaded."
            mv "${book}/$SCAND" .
   
            if [ -s "$SCAND" ]
               then

            # Here we go.... find it, number it.

            MATCHLINE=`cat "$SCAND" | grep -n "<pageType>Title<\/pageType>" | cut -f1 -d':'`
            LESSONE=$((${MATCHLINE} - 1))
            if [ "$LESSONE" -eq "-1" ]
               then
               echo "No title page set!"
               LESSONE=0
            fi
            PAGENUM=`cat "$SCAND" | head -${LESSONE} | tail -1`
            if [ "${PAGENUM}" = '    <page leafNum="0">' ]
               then
                  echo "NO CHANGE NEEDED."
               else
                  # Clean out the Title Pagetype.
                  cat "$SCAND" | sed 's/<pageType>Title</<pageType>Normal</g' > ${1}.cleaned.txt
                  # Let's play swapping the first page.
                  MATCHLINE=`cat ${1}.cleaned.txt | grep -n '<page leafNum="0">' | cut -f1 -d':'`
                  head -${MATCHLINE} ${1}.cleaned.txt > "$SCAND"
                  echo "      <pageType>Title</pageType>" >> "$SCAND"
                  PLUSONE=$((${MATCHLINE} + 2))
                  tail -n +${PLUSONE} ${1}.cleaned.txt >> "$SCAND"
                  ia upload -n "$book" "$SCAND" # Set No-Derive, since it's just fine.
                  ia metadata "$book" -m "coverleaf:0"
                  rm -f "$SCAND" ${1}.cleaned.txt
                  COUNT=$(($COUNT + 1))
             fi
             else
             echo "Whoops, .xml is zero."
            fi
             rmdir "${book}"
             rm -f "$SCAND"
         else
             echo "No scandata.xml for $book."
       fi
    fi
    done

echo "Total items updated: $COUNT"
