# by : Nisarg kanasagra
'''
NOTE Only for the Simple like "π Brand σ Price<100 (Foods)" like only for the simple queries.
TODO make it object based so abdulla and lukka can also do some thing
TODO make it comteble with SQL:
    - For that I Need to learn the SQLAlcamy or SQLlite
TODO Make it stack based  for more larger aplication
'''


pi = "*"
sigma = ""
table = ""

q = input("Enter the query\n")

# print(q)

q = q[::-1]

# Supported Oparations 
oparations = ["π", "σ"]

# Stacks of oprator and oparant
oprators = []
oparants = []

# temp string containing the temparary oparant or oparator
temp = ""

for char in q:
    if char == ")":
        continue
    
    # ( may means table or the group of query
    
    # if table don't contain anything means it is table name
    elif char == "(":
        oprators.append("(")
        oparants.append(temp[::-1].strip())
        temp = ""
        
        
    # for π - select oparator
    elif char == "π":
        oprators.append("π")
        oparants.append(temp[::-1].strip())
        
        temp = ""
        
    # for σ - where oparator
    elif char == "σ":
        oprators.append("σ")
        oparants.append(temp[::-1].strip())
        temp = ""
        
    # for π - select oparator
    else:
        temp+=char
        
print(oparants)
print(oprators)
        
while len(oprators):
    ot = oprators.pop()
    on = oparants.pop()
    if ot == "(":
        table = on

    elif ot == "π":
        if pi == "*":
            pi = on
        else:
            pi += ","+on
            
    elif ot == "σ":
        sigma = on
        
    else:
        raise ValueError
    

        
    
    
ans = f"select {pi} from {table}"

if sigma != "":
    ans += f" where {sigma}"
print(ans)

# oparations = ["π", "σ"]

# oprators = []
# oparants = []
# temp = ""

# for char in q:
#     # temp += char
#     if char == ")":
#         continue
    
#     if char == "(":
#         if  temp!="":
#             oparants.append(temp.strip())
#         temp = ""
#         continue
        
#     if char in oparations:
#         if  temp!="":
#             oparants.append(temp.strip())
#         temp = char
#         oprators.append(temp)
#         temp = ""
#         continue
    
#     temp += char
    
# if temp!="":
#     oparants.append(temp)
    
    