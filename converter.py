# function based version
# by : Nisarg kanasagra

'''
NOTE Only for the Simple like "π Brand σ Price<100 (Foods)" like only for the simple queries.
TODO make it object based so abdulla and lukka can also do some thing
TODO make it comteble with SQL:
    - For that I Need to learn the SQLAlcamy or SQLlite
TODO Make it stack based  for more larger aplication
'''




def term_maker(op : str):
    # use of globle key word for allowing the change in globle variable
    global temp
    '''make the term and append the oparator and oprant in respective stacks'''
    # TODO needed to modify for the binary oparator
    # NOTE done for unary oparator
    oprators.append(op)
    oparants.append(temp[::-1].strip())
    temp = ""

def stack_filler():
    # use of globle key word for allowing the change in globle variable
    global temp
    '''fill the stack through out the query'''

    for char in q:
        if char == ")":
            continue
        
        elif char in oparations:
            term_maker(char)
               
        # making word from char
        else:
            temp += char
        
# print(oparants)
# print(oprators)


def proccessor():  
    # use of globle key word for allowing the change in globle variable
    global oparants      
    global oprators
    global pi,table,sigma      
    while len(oprators):
        ot = oprators.pop()
        on = oparants.pop()
        # ( may means table or the group of query
        # if table don't contain anything means it is table name
        if ot == "(":
            if table == "":
                table = on

        # for π - select oparator
        elif ot == "π":
            if pi == "*":
                pi = on
            else:
                pi += ","+on
                
        # for σ - where oparator
        elif ot == "σ":
            sigma = on
            
        else:
            raise ValueError
    

        
    
def decoder():    
    ans = f"select {pi} from {table}"

    if sigma != "":
        ans += f" where {sigma}"
    print(ans)



if __name__ == "__main__":    
    pi = "*"
    sigma = ""
    table = ""
    # temp string containing the temparary oparant or oparator
    temp = ""

    q = input("Enter the query\n")

    # print(q)

    q = q[::-1]

    # Supported Oparations 
    oparations = ["π", "σ","("]

    # Stacks of oprator and oparant
    oprators = []
    oparants = []

    
    stack_filler()
    proccessor()
    decoder()