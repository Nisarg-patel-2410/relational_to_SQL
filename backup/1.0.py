# by : Nisarg kanasagra

'''
NOTE Only for the Simple like "π Brand σ Price<100 (Foods)"
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

temp = ""
for char in q:
    if char == ")":
        continue
    elif char == "(" and table == "":
        table = temp[::-1].strip()
        temp = ""
        
    elif char == "π":
        pi = temp[::-1].strip()
        temp = ""
        
    elif char == "σ":
        sigma = temp[::-1].strip()
        temp = ""
        
    else:
        temp+=char
        
    
ans = f"select {pi} from {table}"

if sigma != "":
    ans += f"where {sigma}"
print(ans)