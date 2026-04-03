# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 10:46:46 2026

@author: User
"""

from src.recruit_query_exact import RecruitQueryExact, pretty_print_query_result

q = RecruitQueryExact()

payload = q.query_exact(["fire_attribute", "leader", "flat_tits", "damage_output", "weaken"], top_n=10)
pretty_print_query_result(payload)
'''
payload = q.query_exact(["flat_tits", "암속성", "폭발력", "데미지"], top_n=10)
pretty_print_query_result(payload)
'''