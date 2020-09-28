import os
import discord
import re
from dotenv import load_dotenv
from discord.ext import commands
client= commands.Bot(command_prefix='q.')
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
def search_string(book1,book2,string_to_search):     
    """Search for the given string in file and return lines containing that string,
    along with line numbers"""
    line_number = 0
    mylines = [] 
    index= []
    ar1=[r'\W']
    ar1.append(string_to_search.lower())
    ar1.append(r"\W")
    ar2 =''.join(map(str, ar1)) 
    ar2.join(ar1)
    raw=r"{}".format(ar2)
    # Open the file in read only mode
    with open(book1, 'r') as read_obj1:
        for line in read_obj1:
            # For each line, check if line contains the string
            line_number += 1
            if re.search(raw,line.lower()) != None:
                index.append(line_number) 
                k=1
    with open(book2, 'r') as read_obj1:
        # Read all lines in the file one by one
        for line in read_obj1:
            # For each line, check if line contains the string
            line_number += 1
            mylines.append(line) 
    # Return list of all the lines and line number where string is found
    return mylines,index

@client.command(pass_context=True)
async def f(ctx,*,arg):
    if ctx.message.author == client.user:
        return  #None 
    msg=list(arg.upper())
    channel=['752193632383008770','752196383066554538']
    whitelist=['A','B','C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W','X', 'Y', 'Z',0,1,2,3,4,5,6,7,8,9,'!','?',' ','.',';',',','"',"'",'…','*','-',':']
    if str(ctx.channel.id) in channel:
        # if msg in whitelist:
        k=0
        if all(elem in whitelist for elem in msg):
            def qt(arg1):
                file1 = "/app/Harry Potter and the Prince of Slytherin_pt.txt"
                file2 = "/app/Harry Potter and the Prince of Slytherin_md.txt"
                bo,lin=search_string(file1,file2,arg1)
                a = [x - 1 for x in lin]
                res= []
                chap= []
                t=". HP&"
                try:
                    for i in range(1):
                        res.append(bo[a[i]].rstrip())
                        next1=a[i]
                        k=1
                except IndexError:
                    k=0
                    return 'err','err',k
                for i in range(next1,0,-1):
                    if t in bo[i]:
                        chap.append(bo[i])
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
                str1='%.2047s' % str1
                return str1,chap[0],k
        def chapter(chap1):
            c=list(chap1)
            ct=0
            ct1=0
            co=0
            chno=[]
            p1=[]
            for i in range(0,len(c)):
                ct+=1
                if '&' == c[i]:
                    p1.append(ct)
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
            for i in range(0,len(c)):
                ct1+=1
                if '.' == c[i]:
                    co=ct1
            for i in range(0,co-1):
                chno.append(c[i])
            chno=''.join(chno) 
            chno=filter(str.isdigit, chno) 
            chno=''.join(chno)
            url="\nhttps://www.fanfiction.net/s/11191235/"+chno+"/Harry-Potter-and-the-Prince-of-Slytherin"
            return tit,url
        des,chap,k=qt(arg)
        if k==1:
            tit,url1=chapter(chap)
            embed1=discord.Embed(title=''.join(tit),
                url=url1,
                description=des,
                colour=discord.Colour(0x272b28))
        embed2=discord.Embed(
            description="Quote not found!",
            colour=discord.Colour(0x272b28))
        if k==1:
            await ctx.send(embed=embed1) 
        else:
            await ctx.send(embed=embed2)                 

@client.command(pass_context=True)
async def fhelp(ctx):
    if ctx.message.author == client.user:
        return  #None 
    des="To use the bot, use the command- `q.f QUOTE`"+'\n'+"For eg- `q.f Voldemort is back`"+'\n\n'+"Github Repo- https://github.com/Roguedev1/Quote-Finder"+'\n'+"Contact the developer for any queries- @RogueOne"
    embed1=discord.Embed(title='Info',
                description=des,
                colour=discord.Colour(0x272b28))
    await ctx.send(embed=embed1)   
client.run(TOKEN)

