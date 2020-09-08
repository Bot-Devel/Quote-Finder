import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
client= commands.Bot(command_prefix='q.')
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
def search_string(file_name, string_to_search):     
    """Search for the given string in file and return lines containing that string,
    along with line numbers"""
    line_number = 0
    mylines = [] 
    index= []
    # Open the file in read only mode
    with open(file_name, 'r') as read_obj:
        # Read all lines in the file one by one
        for line in read_obj:
            # For each line, check if line contains the string
            line_number += 1
            mylines.append(line) 
            if string_to_search.lower() in line.lower():
                # If yes, then add the line number in the list
                index.append(line_number) 
    # Return list of all the lines and line number where string is found
    return mylines,index

@client.command(pass_context=True)
async def f(ctx,*,arg):
    if ctx.message.author == client.user:
        return  #None 
    msg=list(arg.upper())
    channel=['752193632383008770','752196383066554538']
    whitelist=['A','B','C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W','X', 'Y', 'Z',0,1,2,3,4,5,6,7,8,9,'!','?',' ','.',';',',','"',"'",'…']
    if str(ctx.channel.id) in channel:
        # if msg in whitelist:
        if all(elem in whitelist for elem in msg):
            def qt(arg1):
                file1 = "/app/Harry Potter and the Prince of Slytherin.txt"
                bo,lin=search_string(file1, arg1)
                a = [x - 1 for x in lin]
                res= []
                chap= []
                t=". HP&"
                for i in range(1):
                    res.append(bo[a[i]].rstrip())
                    next1=a[i]
                for i in range(next1,0,-1):
                    if t in bo[i]:
                        chap.append(bo[i]) #appends the chapter name to the list
                next1+=2
                next1= bo[next1]
                str1 = ""    
                for i in range(1):
                    i=res[0]
                    str1 += i
                    str1+="\n \n"
                    str1+=next1
                if len(chap) == 0:
                    chap.append("0. HP&POS 0: First Page") #dummy book+chap name
                return str1,chap[0]
        def chapter(chap1):
            c=list(chap1)
            ct=0
            m='&'
            p1=[]
            for i in range(0,len(c)):
                ct+=1
                if m == c[i]:
                    p1.append(ct) #found &
            p=p1[0]
            p+=3
            chap1=['C','h','a','p','t','e','r',' ']
            book=[]
            tit= []
            for i in range(p,len(c)):             
                chap1.append(c[i])
            for i in range(0,p):                 
                book.append(c[i])
            book.append(" | ")
            tit=book+chap1
            return tit     
        des,chap=qt(arg)
        tit=chapter(chap)
        embed1=discord.Embed(title=''.join(tit),
            description=des,
            colour=discord.Colour(0x272b28))
        await ctx.send(embed=embed1) 
            # await ctx.send(qt(arg)) #output without embed                
client.run(TOKEN)
