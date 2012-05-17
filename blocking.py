from collections import defaultdict
from itertools import product, chain
from math import sqrt, log

def hashPair(pair) :
      return tuple(sorted([tuple(sorted(pair[0].items())), tuple(sorted(pair[1].items()))]))


def predicateCoverage(pairs, predicates) :
    coverage = defaultdict(list)
    for pair in pairs :
        for predicate, field in predicates :
            keys1 = predicate(pair[0][field])
            keys2 = predicate(pair[1][field])
            if set(keys1) & set(keys2) :
                coverage[(predicate,field)].append(pair)
              
    return(coverage)


# Approximate learning of blocking following the ApproxRBSetCover from
# page 102 of Bilenko
def trainBlocking(training_pairs, predicates, data_model, eta, epsilon) :

  training_distinct, training_dupes = training_pairs
  n_training_dupes = len(training_dupes)
  n_training_distinct = len(training_distinct)
  sample_size = n_training_dupes + n_training_distinct

  # The set of all predicate functions operating over all fields
  predicateSet = list(product(predicates, data_model['fields']))
  n_predicates = len(predicateSet)

  
  found_dupes = predicateCoverage(training_dupes,
                                  predicateSet)
  found_distinct = predicateCoverage(training_distinct,
                                     predicateSet)


  predicateSet = found_dupes.keys() 

  # We want to throw away the predicates that puts together too many
  # distinct pairs
  eta = sample_size * eta

  [predicateSet.remove(predicate)
   for predicate in found_distinct
   if len(found_distinct[predicate]) >= eta]

  # We don't want to penalize a blocker if it puts distinct pairs
  # together that look like they could be duplicates. Here we compute
  # the expected number of predicates that will cover a duplicate pair
  # We'll remove all the distince pairs from consideration if they are
  # covered by many predicates
  expected_dupe_cover = sqrt(n_predicates / log(n_training_dupes))

  predicate_count = defaultdict(int)
  for pair in chain(*found_distinct.values()) :
      predicate_count[hashPair(pair)] += 1

  training_distinct = [pair for pair in training_distinct
                       if predicate_count[hashPair(pair)] < expected_dupe_cover]


  found_distinct = predicateCoverage(training_distinct,
                                     predicateSet)

  # Greedily find the predicates that, at each step, covers the most
  # duplicates and covers the least distinct pairs, dute to Chvatal, 1979
  finalPredicateSet = []
  print "Uncovered dupes"
  print n_training_dupes
  while n_training_dupes >= epsilon :

    optimumCover = 0
    bestPredicate = None
    for predicate in predicateSet :
      try:  
          cover = (len(found_dupes[predicate])
                   / float(len(found_distinct[predicate]))
                   )
      except ZeroDivisionError:
          cover = len(found_dupes[predicate])

      if cover > optimumCover :
        optimumCover = cover
        bestPredicate = predicate


    if not bestPredicate :
        print "Ran out of predicates"
        break

    predicateSet.remove(bestPredicate)
    n_training_dupes -= len(found_dupes[bestPredicate])
    [training_dupes.remove(pair) for pair in found_dupes[bestPredicate]]
    found_dupes = predicateCoverage(training_dupes,
                                    predicateSet)

    print n_training_dupes

    finalPredicateSet.append(bestPredicate)
    
  print "FINAL PREDICATE SET!!!!"
  print finalPredicateSet

  return finalPredicateSet

#returns the field as a tuple
def wholeFieldPredicate(field) :
  return (field, )
  
#returns the tokens in the field as a tuple, split on whitespace
def tokenFieldPredicate(field) :
  return field.split()

# Contain common integer
def commonIntegerPredicate(field) :
    import re
    return re.findall("\d+", field)

def nearIntegersPredicate(field) :
    import re
    ints = sorted([int(i) for i in re.findall("\d+", field)])
    return [(i-1, i, i+1) for i in ints]

def commonFourGram(field) :
    return [field[pos:pos + 4] for pos in xrange(0, len(field), 4)]

def commonSixGram(field) :
    return [field[pos:pos + 6] for pos in xrange(0, len(field), 6)]

def sameThreeCharStartPredicate(field) :
    return (field[:3],)

def sameFiveCharStartPredicate(field) :
    return (field[:5],)

def sameSevenCharStartPredicate(field) :
    return (field[:7],)

if __name__ == '__main__':
  import dedupe

  field = '123 16th st'
  print wholeFieldPredicate(field) == ('123 16th st',)
  print tokenFieldPredicate(field) == ['123', '16th', 'st']
  print commonIntegerPredicate(field) == ['123', '16']
  print sameThreeCharStartPredicate(field) == ('123',)
  print sameFiveCharStartPredicate(field) == ('123 1',)
  print sameSevenCharStartPredicate(field) == ('123 16t',)
  print nearIntegersPredicate(field) == [(15, 16, 17), (122, 123, 124)]
  print commonFourGram(field) == ['123 ', '16th', ' st']
  print commonSixGram(field) == ['123 16', 'th st']


  numTrainingPairs = 64000
  data_d, header, duplicates_s = dedupe.canonicalImport("./datasets/restaurant-nophone-training.csv")
  data_model = dedupe.dataModel()

  training_pairs = dedupe.createTrainingPairs(data_d, duplicates_s, numTrainingPairs)

  trainBlocking(training_pairs,
                (wholeFieldPredicate,
                 tokenFieldPredicate,
                 commonIntegerPredicate,
                 sameThreeCharStartPredicate,
                 sameFiveCharStartPredicate,
                 sameSevenCharStartPredicate,
                 nearIntegersPredicate,
                 commonFourGram,
                 commonSixGram),
                data_model, 1, 1)  