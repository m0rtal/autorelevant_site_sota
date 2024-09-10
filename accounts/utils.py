from string import ascii_letters, digits  
from random import choice 
 
lettersdigits = 'ABDEFHKLMNPRSTWXYZ' + digits 
 
def random_human_code(n): 
   my_list = [choice(lettersdigits) for _ in range(n)] 
   my_str = ''.join(my_list) 
   return my_str 
