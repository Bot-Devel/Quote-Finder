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
    ar1=[r'\b']
    ar1.append(string_to_search.lower())
    ar1.append(r"\b")
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
                # file1 = "/home/arbaaz/Personal/Bots/Quote Finder/Harry Potter and the Prince of Slytherin_pt.txt" #plain text
                # file2= "/home/arbaaz/Personal/Bots/Quote Finder/Harry Potter and the Prince of Slytherin_md.txt" #markdown text
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
                return str1,chap[0],k
        def chapter(chap1):
            c=list(chap1)
            ct=0
            # m='&'
            p1=[]
            for i in range(0,len(c)):
                ct+=1
                if '&' == c[i]:
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
        des,chap,k=qt(arg)
        if k==1:
            tit=chapter(chap)
            embed1=discord.Embed(title=''.join(tit),
                description=des,
                colour=discord.Colour(0x272b28))
        embed2=discord.Embed(
            description="Quote not found!",
            colour=discord.Colour(0x272b28))
        if k==1:
            await ctx.send(embed=embed1) 
        else:
            await ctx.send(embed=embed2)  
            # await ctx.send(qt(arg)) #output without embed                

@client.command(pass_context=True)
async def fhelp(ctx):
    if ctx.message.author == client.user:
        return  #None 
    des="To use the bot, use the following command- `q.f QUOTE`"+'\n'+"**Replace the single quotation `'` with double quotation symbol in the following paragraphs, i m using the single quotation just to illustrate because double quotation is used to start a string in Python.**"+'\n'+"Note- Do not use any quote ending with `.`or `'` or `.'` or `!'` **if** the line from the POS fanfic itself ends with `!'` or `.'` since the code that i am using wont be able to search a quote ending with `.` unless an alphanumeric character immediately follows that dot. It might be fixed in the future."+'\n'+"Ref- https://stackoverflow.com/questions/18004955/regex-using-word-boundary-but-word-ends-with-a-period"+'\n\n'+"For example-"+'\n'+"In the line from the fanfic- `'Our Jim did it?' said James in wonder. 'It's ... a miracle!'`"+'\n'+"The following command wont work-"+'\n'+"`q.f James in wonder.`"+'\n'+"But `q.f James in wonder. '` will work."+'\n\n'+"The following command wont work-`q.f It's ... a miracle!'` and `q.f It's ... a miracle!`But `q.f It's ... a miracle` will work."+'\n\n'+"**TL;DR: Its safer to not use `.`,`!`,`'` at the end of the quote unless you know there is a word after it."+'\n'+"Eg- `q.f It's ... a miracle`**"+'\n\n'+"Github Repo of the bot-https://github.com/Roguedev1/Quote-Finder"
   
    embed1=discord.Embed(title='Quick Doc',
                description=des,
                colour=discord.Colour(0x272b28))
    await ctx.send(embed=embed1)   
client.run(TOKEN)

