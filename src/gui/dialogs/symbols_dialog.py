# unicode math symbol picker dialog

import customtkinter as ctk
from typing import Optional, Callable, List, Tuple, Dict

from .centered_dialog import CenteredDialog
from ...utils.shortcuts import bind_entry_shortcuts

# performance tuning
SEARCH_DEBOUNCE_MS = 150  # delay before search triggers


# symbol groups organized by category
# symbols within each group are ordered by frequency of use

# --- CORE MATHEMATICS ---

BASIC_ARITHMETIC = [
    ("+", "PLUS SIGN", "Addition"),
    ("\u2212", "MINUS SIGN", "Subtraction"),
    ("\u00d7", "MULTIPLICATION SIGN", "Multiplication"),
    ("\u00f7", "DIVISION SIGN", "Division"),
    ("\u00b1", "PLUS-MINUS SIGN", "Plus or minus"),
    ("\u2213", "MINUS-OR-PLUS SIGN", "Minus or plus"),
    ("\u22c5", "DOT OPERATOR", "Multiplication, dot product"),
    ("\u2217", "ASTERISK OPERATOR", "Convolution, multiplication"),
    ("/", "SOLIDUS", "Division"),
    ("\u2044", "FRACTION SLASH", "Fraction separator"),
]

EQUALITY_INEQUALITY = [
    ("=", "EQUALS SIGN", "Equality"),
    ("\u2260", "NOT EQUAL TO", "Inequality"),
    ("<", "LESS-THAN SIGN", "Less than"),
    (">", "GREATER-THAN SIGN", "Greater than"),
    ("\u2264", "LESS-THAN OR EQUAL TO", "Less than or equal"),
    ("\u2265", "GREATER-THAN OR EQUAL TO", "Greater than or equal"),
    ("\u226a", "MUCH LESS-THAN", "Much less than"),
    ("\u226b", "MUCH GREATER-THAN", "Much greater than"),
    ("\u226e", "NOT LESS-THAN", "Not less than"),
    ("\u226f", "NOT GREATER-THAN", "Not greater than"),
    ("\u2270", "NEITHER LESS-THAN NOR EQUAL TO", "Neither less nor equal"),
    ("\u2271", "NEITHER GREATER-THAN NOR EQUAL TO", "Neither greater nor equal"),
    ("\u22d8", "VERY MUCH LESS-THAN", "Very much less than"),
    ("\u22d9", "VERY MUCH GREATER-THAN", "Very much greater than"),
    ("\u22d6", "LESS-THAN WITH DOT", "Less than with dot"),
    ("\u22d7", "GREATER-THAN WITH DOT", "Greater than with dot"),
]

EQUIVALENCE_APPROXIMATION = [
    ("\u2261", "IDENTICAL TO", "Identical, congruent modulo"),
    ("\u2262", "NOT IDENTICAL TO", "Not identical"),
    ("\u2245", "APPROXIMATELY EQUAL TO", "Congruent, isomorphic"),
    ("\u2246", "APPROXIMATELY BUT NOT ACTUALLY EQUAL TO", "Approximately but not equal"),
    ("\u2247", "NEITHER APPROXIMATELY NOR ACTUALLY EQUAL TO", "Neither approximately nor equal"),
    ("\u2248", "ALMOST EQUAL TO", "Approximately equal"),
    ("\u2249", "NOT ALMOST EQUAL TO", "Not approximately equal"),
    ("\u224a", "ALMOST EQUAL OR EQUAL TO", "Almost equal or equal"),
    ("\u224b", "TRIPLE TILDE", "Triple tilde"),
    ("\u224c", "ALL EQUAL TO", "All equal to"),
    ("\u224d", "EQUIVALENT TO", "Equivalent to"),
    ("\u224e", "GEOMETRICALLY EQUIVALENT TO", "Geometrically equivalent"),
    ("\u224f", "DIFFERENCE BETWEEN", "Difference between"),
    ("\u2250", "APPROACHES THE LIMIT", "Approaches limit"),
    ("\u2251", "GEOMETRICALLY EQUAL TO", "Geometrically equal"),
    ("\u223c", "TILDE OPERATOR", "Similar to, proportional"),
    ("\u223d", "REVERSED TILDE", "Reversed tilde"),
    ("\u226c", "BETWEEN", "Between"),
    ("\u221d", "PROPORTIONAL TO", "Proportional to"),
]

DEFINITION_ASSIGNMENT = [
    ("\u2254", "COLON EQUALS", "Definition"),
    ("\u2255", "EQUALS COLON", "Definition (reversed)"),
    ("\u225c", "DELTA EQUAL TO", "Defined as"),
    ("\u225d", "EQUAL TO BY DEFINITION", "Equal by definition"),
    ("\u225e", "MEASURED BY", "Measured by"),
    ("\u225f", "QUESTIONED EQUAL TO", "Questioned equal"),
]

ORDER_RELATIONS = [
    ("\u227a", "PRECEDES", "Precedes"),
    ("\u227b", "SUCCEEDS", "Succeeds"),
    ("\u227c", "PRECEDES OR EQUAL TO", "Precedes or equal"),
    ("\u227d", "SUCCEEDS OR EQUAL TO", "Succeeds or equal"),
    ("\u227e", "PRECEDES OR EQUIVALENT TO", "Precedes or equivalent"),
    ("\u227f", "SUCCEEDS OR EQUIVALENT TO", "Succeeds or equivalent"),
    ("\u2280", "DOES NOT PRECEDE", "Does not precede"),
    ("\u2281", "DOES NOT SUCCEED", "Does not succeed"),
    ("\u2272", "LESS-THAN OR EQUIVALENT TO", "Less than or equivalent"),
    ("\u2273", "GREATER-THAN OR EQUIVALENT TO", "Greater than or equivalent"),
    ("\u22de", "EQUAL TO OR PRECEDES", "Equal or precedes"),
    ("\u22df", "EQUAL TO OR SUCCEEDS", "Equal or succeeds"),
]

ROOTS_POWERS = [
    ("\u221a", "SQUARE ROOT", "Square root"),
    ("\u221b", "CUBE ROOT", "Cube root"),
    ("\u221c", "FOURTH ROOT", "Fourth root"),
    ("\u221e", "INFINITY", "Infinity"),
]

# --- CALCULUS & ANALYSIS ---

CALCULUS_DIFFERENTIAL = [
    ("\u2202", "PARTIAL DIFFERENTIAL", "Partial derivative"),
    ("\u2207", "NABLA", "Del, gradient operator"),
    ("\u2206", "INCREMENT", "Increment, Laplacian"),
    ("\u2146", "DIFFERENTIAL D", "Differential d"),
    ("\u2032", "PRIME", "Derivative, minutes"),
    ("\u2033", "DOUBLE PRIME", "Second derivative, seconds"),
    ("\u2034", "TRIPLE PRIME", "Third derivative"),
    ("\u2057", "QUADRUPLE PRIME", "Fourth derivative"),
]

CALCULUS_INTEGRALS = [
    ("\u222b", "INTEGRAL", "Integral"),
    ("\u222c", "DOUBLE INTEGRAL", "Double integral"),
    ("\u222d", "TRIPLE INTEGRAL", "Triple integral"),
    ("\u222e", "CONTOUR INTEGRAL", "Contour integral"),
    ("\u222f", "SURFACE INTEGRAL", "Surface integral"),
    ("\u2230", "VOLUME INTEGRAL", "Volume integral"),
    ("\u2231", "CLOCKWISE INTEGRAL", "Clockwise integral"),
    ("\u2232", "CLOCKWISE CONTOUR INTEGRAL", "Clockwise contour"),
    ("\u2233", "ANTICLOCKWISE CONTOUR INTEGRAL", "Anticlockwise contour"),
    ("\u2320", "TOP HALF INTEGRAL", "Top half integral"),
    ("\u2321", "BOTTOM HALF INTEGRAL", "Bottom half integral"),
    ("\u2a0c", "QUADRUPLE INTEGRAL OPERATOR", "Quadruple integral"),
    ("\u2a0d", "FINITE PART INTEGRAL", "Finite part integral"),
    ("\u2a0e", "INTEGRAL WITH DOUBLE STROKE", "Integral double stroke"),
    ("\u2a0f", "INTEGRAL AVERAGE WITH SLASH", "Integral average"),
    ("\u2a10", "CIRCULATION FUNCTION", "Circulation"),
    ("\u2a11", "ANTICLOCKWISE INTEGRATION", "Anticlockwise integration"),
    ("\u2a12", "LINE INTEGRATION WITH RECTANGULAR PATH", "Rectangular path"),
    ("\u2a13", "LINE INTEGRATION WITH SEMICIRCULAR PATH", "Semicircular path"),
    ("\u2a14", "LINE INTEGRATION NOT INCLUDING THE POLE", "Not including pole"),
    ("\u2a15", "INTEGRAL AROUND A POINT OPERATOR", "Around point"),
    ("\u2a16", "QUATERNION INTEGRAL OPERATOR", "Quaternion integral"),
    ("\u2a17", "INTEGRAL WITH LEFTWARDS ARROW WITH HOOK", "Integral with arrow"),
    ("\u2a18", "INTEGRAL WITH TIMES SIGN", "Integral with times"),
    ("\u2a19", "INTEGRAL WITH INTERSECTION", "Integral with intersection"),
    ("\u2a1a", "INTEGRAL WITH UNION", "Integral with union"),
    ("\u2a1b", "INTEGRAL WITH OVERBAR", "Integral with overbar"),
    ("\u2a1c", "INTEGRAL WITH UNDERBAR", "Integral with underbar"),
]

CALCULUS_SUMMATION = [
    ("\u2211", "N-ARY SUMMATION", "Summation"),
    ("\u220f", "N-ARY PRODUCT", "Product"),
    ("\u2210", "N-ARY COPRODUCT", "Coproduct"),
    ("\u2a00", "N-ARY CIRCLED DOT OPERATOR", "Circled dot operator"),
    ("\u2a01", "N-ARY CIRCLED PLUS OPERATOR", "Circled plus operator"),
    ("\u2a02", "N-ARY CIRCLED TIMES OPERATOR", "Circled times operator"),
    ("\u2a03", "N-ARY UNION OPERATOR WITH DOT", "Union with dot"),
    ("\u2a04", "N-ARY UNION OPERATOR WITH PLUS", "Union with plus"),
    ("\u2a05", "N-ARY SQUARE INTERSECTION OPERATOR", "Square intersection"),
    ("\u2a06", "N-ARY SQUARE UNION OPERATOR", "Square union"),
    ("\u2a07", "TWO LOGICAL AND OPERATOR", "Two logical AND"),
    ("\u2a08", "TWO LOGICAL OR OPERATOR", "Two logical OR"),
    ("\u2a09", "N-ARY TIMES OPERATOR", "N-ary times"),
    ("\u2a0a", "MODULO TWO SUM", "Modulo two sum"),
    ("\u2a0b", "SUMMATION WITH INTEGRAL", "Summation integral"),
]

# --- STATISTICS & PROBABILITY ---

STATISTICS_PROBABILITY = [
    ("\U0001d53c", "MATHEMATICAL DOUBLE-STRUCK CAPITAL E", "Expected value"),
    ("\U0001d54d", "MATHEMATICAL DOUBLE-STRUCK CAPITAL V", "Variance"),
    ("\u2119", "DOUBLE-STRUCK CAPITAL P", "Probability"),
    ("\u03c3", "GREEK SMALL LETTER SIGMA", "Standard deviation"),
    ("\u03bc", "GREEK SMALL LETTER MU", "Population mean"),
    ("\u03c1", "GREEK SMALL LETTER RHO", "Correlation coefficient"),
    ("\u03c7", "GREEK SMALL LETTER CHI", "Chi (χ² distribution)"),
    ("\u03bd", "GREEK SMALL LETTER NU", "Degrees of freedom"),
    ("\u03b2", "GREEK SMALL LETTER BETA", "Regression coefficient"),
    ("\u03b5", "GREEK SMALL LETTER EPSILON", "Error term"),
    ("\u03b7", "GREEK SMALL LETTER ETA", "Effect size"),
    ("\u03bb", "GREEK SMALL LETTER LAMBDA", "Rate parameter"),
    ("\u03b8", "GREEK SMALL LETTER THETA", "Parameter"),
    ("\u03c4", "GREEK SMALL LETTER TAU", "Kendall's tau"),
    ("\u03ba", "GREEK SMALL LETTER KAPPA", "Cohen's kappa"),
    ("\u22a5", "UP TACK", "Independence"),
    ("\u2aeb", "DOUBLE-ENDED MULTIMAP", "Independence (alternate)"),
    ("\u2223", "DIVIDES", "Conditional (given)"),
    ("\u2016", "DOUBLE VERTICAL LINE", "Parallel, norm"),
    ("\u223c", "TILDE OPERATOR", "Distributed as"),
    ("\u2241", "NOT TILDE", "Not distributed as"),
    ("\u2a7d", "SLANTED EQUAL TO OR LESS-THAN", "Stochastic dominance"),
    ("\u2a7e", "SLANTED EQUAL TO OR GREATER-THAN", "Stochastic dominance"),
]

MEANS_BAR_ABOVE = [
    ("x\u0304", "X BAR", "Sample mean"),
    ("\u0233", "Y BAR", "Sample mean of y"),
    ("z\u0304", "Z BAR", "Sample mean of z"),
    ("p\u0304", "P BAR", "Sample proportion"),
    ("q\u0304", "Q BAR", "Complement proportion"),
    ("r\u0304", "R BAR", "Mean radius/rate"),
    ("v\u0304", "V BAR", "Mean velocity"),
    ("\u0101", "A BAR", "Mean acceleration"),
    ("t\u0304", "T BAR", "Mean time"),
    ("n\u0304", "N BAR", "Mean count"),
    ("\u03bc\u0304", "MU BAR", "Mean of means"),
    ("\u03c3\u0304", "SIGMA BAR", "Mean standard deviation"),
    ("\u03b8\u0304", "THETA BAR", "Mean angle"),
    ("\u03c9\u0304", "OMEGA BAR", "Mean angular velocity"),
]

ESTIMATES_HAT = [
    ("x\u0302", "X HAT", "Estimated x"),
    ("\u0177", "Y HAT", "Predicted y value"),
    ("p\u0302", "P HAT", "Estimated proportion"),
    ("q\u0302", "Q HAT", "Estimated complement"),
    ("\u03b2\u0302", "BETA HAT", "Estimated coefficient"),
    ("\u03b8\u0302", "THETA HAT", "Estimated parameter"),
    ("\u03bc\u0302", "MU HAT", "Estimated mean"),
    ("\u03c3\u0302", "SIGMA HAT", "Estimated std deviation"),
    ("\u03bb\u0302", "LAMBDA HAT", "Estimated rate"),
    ("\u03c1\u0302", "RHO HAT", "Estimated correlation"),
    ("\u03c0\u0302", "PI HAT", "Estimated probability"),
    ("\u03b1\u0302", "ALPHA HAT", "Estimated alpha"),
    ("\u03c4\u0302", "TAU HAT", "Estimated tau"),
    ("\u00ee", "I HAT", "Unit vector i"),
    ("\u0135", "J HAT", "Unit vector j"),
    ("k\u0302", "K HAT", "Unit vector k"),
    ("n\u0302", "N HAT", "Unit normal vector"),
    ("r\u0302", "R HAT", "Unit radial vector"),
]

DERIVATIVES_DOT = [
    ("\u1e8b", "X DOT", "First derivative of x (dx/dt)"),
    ("\u1e8d", "X DOUBLE DOT", "Second derivative of x"),
    ("\u1e8f", "Y DOT", "First derivative of y"),
    ("y\u0308", "Y DOUBLE DOT", "Second derivative of y"),
    ("\u017c", "Z DOT", "First derivative of z"),
    ("z\u0308", "Z DOUBLE DOT", "Second derivative of z"),
    ("\u1e59", "R DOT", "Radial velocity"),
    ("r\u0308", "R DOUBLE DOT", "Radial acceleration"),
    ("\u03b8\u0307", "THETA DOT", "Angular velocity"),
    ("\u03b8\u0308", "THETA DOUBLE DOT", "Angular acceleration"),
    ("\u03c6\u0307", "PHI DOT", "Angular velocity (phi)"),
    ("\u03c6\u0308", "PHI DOUBLE DOT", "Angular acceleration (phi)"),
    ("\u03c8\u0307", "PSI DOT", "Angular velocity (psi)"),
    ("q\u0307", "Q DOT", "Generalized velocity"),
    ("q\u0308", "Q DOUBLE DOT", "Generalized acceleration"),
    ("\u1e57", "P DOT", "Momentum derivative"),
    ("\u1e6a", "T DOT", "Temperature rate"),
    ("\u1e41", "M DOT", "Mass flow rate"),
    ("Q\u0307", "Q DOT (CAPITAL)", "Heat transfer rate"),
    ("\u1e86", "W DOT", "Power (work rate)"),
    ("\u03b5\u0307", "EPSILON DOT", "Strain rate"),
]

VECTORS_ARROW = [
    ("a\u20d7", "A VECTOR", "Acceleration vector"),
    ("b\u20d7", "B VECTOR", "Vector b"),
    ("c\u20d7", "C VECTOR", "Vector c"),
    ("d\u20d7", "D VECTOR", "Displacement vector"),
    ("e\u20d7", "E VECTOR", "Electric field vector"),
    ("f\u20d7", "F VECTOR", "Force vector"),
    ("g\u20d7", "G VECTOR", "Gravitational field"),
    ("h\u20d7", "H VECTOR", "Magnetic field intensity"),
    ("i\u20d7", "I VECTOR", "Current density"),
    ("j\u20d7", "J VECTOR", "Current density"),
    ("k\u20d7", "K VECTOR", "Wave vector"),
    ("l\u20d7", "L VECTOR", "Angular momentum"),
    ("m\u20d7", "M VECTOR", "Magnetic moment"),
    ("n\u20d7", "N VECTOR", "Normal vector"),
    ("p\u20d7", "P VECTOR", "Momentum vector"),
    ("q\u20d7", "Q VECTOR", "Position vector"),
    ("r\u20d7", "R VECTOR", "Position/radius vector"),
    ("s\u20d7", "S VECTOR", "Displacement vector"),
    ("t\u20d7", "T VECTOR", "Tangent vector"),
    ("u\u20d7", "U VECTOR", "Velocity vector"),
    ("v\u20d7", "V VECTOR", "Velocity vector"),
    ("w\u20d7", "W VECTOR", "Angular velocity"),
    ("x\u20d7", "X VECTOR", "Position vector x"),
    ("y\u20d7", "Y VECTOR", "Position vector y"),
    ("z\u20d7", "Z VECTOR", "Position vector z"),
    ("\u03c9\u20d7", "OMEGA VECTOR", "Angular velocity vector"),
    ("\u03c4\u20d7", "TAU VECTOR", "Torque vector"),
    ("\u03b1\u20d7", "ALPHA VECTOR", "Angular acceleration"),
    ("\u03bc\u20d7", "MU VECTOR", "Magnetic dipole moment"),
    ("\u2207\u20d7", "NABLA VECTOR", "Del operator (vector)"),
]

TILDE_TRANSFORM = [
    ("x\u0303", "X TILDE", "Approximation of x"),
    ("\u1ef9", "Y TILDE", "Approximation of y"),
    ("f\u0303", "F TILDE", "Fourier transform"),
    ("g\u0303", "G TILDE", "Transform of g"),
    ("\u0169", "U TILDE", "Transformed u"),
    ("\u1e7d", "V TILDE", "Transformed v"),
    ("p\u0303", "P TILDE", "Transformed probability"),
    ("\u03b8\u0303", "THETA TILDE", "Approximate theta"),
    ("\u03b2\u0303", "BETA TILDE", "Approximate beta"),
    ("\u03c3\u0303", "SIGMA TILDE", "Approximate sigma"),
    ("\u03c1\u0303", "RHO TILDE", "Approximate rho"),
    ("\u03c9\u0303", "OMEGA TILDE", "Approximate frequency"),
    ("\u00f1", "N TILDE", "Approximate count"),
    ("\u00c3", "A TILDE (CAPITAL)", "Matrix transform"),
    ("H\u0303", "H TILDE", "Transformed Hamiltonian"),
]

DOUBLE_BAR_TENSOR = [
    ("x\u033f", "X DOUBLE BAR", "Grand mean"),
    ("\u0233\u0304", "Y DOUBLE BAR", "Grand mean of y"),
    ("\u03c3\u033f", "SIGMA DOUBLE BAR", "Stress tensor"),
    ("\u03b5\u033f", "EPSILON DOUBLE BAR", "Strain tensor"),
    ("\u03c4\u033f", "TAU DOUBLE BAR", "Shear stress tensor"),
    ("I\u033f", "I DOUBLE BAR", "Identity tensor"),
    ("T\u033f", "T DOUBLE BAR", "Tensor T"),
    ("F\u033f", "F DOUBLE BAR", "Deformation gradient"),
]

COMBINATIONS_OTHER = [
    ("\u2202\u0304", "D-BAR", "Cauchy-Riemann operator"),
    ("\u2207\u00b2", "DEL SQUARED", "Laplacian operator"),
    ("x\u030a", "X RING", "Special notation"),
    ("\u1e97", "T DOUBLE DOT", "Proper time derivative"),
    ("c\u0304", "C BAR", "Mean concentration"),
    ("\u03c1\u0304", "RHO BAR", "Mean density"),
    ("T\u0304", "T BAR", "Mean temperature"),
    ("P\u0304", "P BAR", "Mean pressure"),
    ("\u0112", "E BAR", "Mean energy"),
    ("V\u0304", "V BAR (CAPITAL)", "Mean volume/molar volume"),
    ("H\u0304", "H BAR", "Mean enthalpy"),
    ("S\u0304", "S BAR", "Mean entropy"),
    ("\u1e20", "G BAR", "Mean Gibbs energy"),
]

COMBINING_DIACRITICALS = [
    ("\u0304", "COMBINING MACRON", "Bar above (mean: x̄)"),
    ("\u0302", "COMBINING CIRCUMFLEX ACCENT", "Hat/caret above (estimate: x̂)"),
    ("\u0303", "COMBINING TILDE", "Tilde above (approximation: x̃)"),
    ("\u0307", "COMBINING DOT ABOVE", "Dot above (derivative: ẋ)"),
    ("\u0308", "COMBINING DIAERESIS", "Double dot above (2nd derivative: ẍ)"),
    ("\u20db", "COMBINING THREE DOTS ABOVE", "Triple dot (3rd derivative)"),
    ("\u030a", "COMBINING RING ABOVE", "Ring above (Ångström)"),
    ("\u0301", "COMBINING ACUTE ACCENT", "Acute accent"),
    ("\u0300", "COMBINING GRAVE ACCENT", "Grave accent"),
    ("\u20d7", "COMBINING RIGHT ARROW ABOVE", "Vector arrow (v⃗)"),
    ("\u20d1", "COMBINING RIGHT HARPOON ABOVE", "Right harpoon above"),
    ("\u20d0", "COMBINING LEFT HARPOON ABOVE", "Left harpoon above"),
    ("\u20d6", "COMBINING LEFT ARROW ABOVE", "Left arrow above"),
    ("\u20e1", "COMBINING LEFT RIGHT ARROW ABOVE", "Bidirectional arrow above"),
    ("\u0332", "COMBINING LOW LINE", "Underline"),
    ("\u0331", "COMBINING MACRON BELOW", "Bar below"),
    ("\u0323", "COMBINING DOT BELOW", "Dot below"),
    ("\u20d2", "COMBINING LONG VERTICAL LINE OVERLAY", "Vertical line overlay"),
    ("\u20d3", "COMBINING SHORT VERTICAL LINE OVERLAY", "Short vertical overlay"),
    ("\u20d8", "COMBINING RING OVERLAY", "Ring overlay"),
    ("\u20da", "COMBINING ANTICLOCKWISE ARROW ABOVE", "Anticlockwise arrow"),
    ("\u20d9", "COMBINING CLOCKWISE ARROW ABOVE", "Clockwise arrow"),
    ("\u20dc", "COMBINING ANTICLOCKWISE RING OVERLAY", "Anticlockwise ring"),
    ("\u20dd", "COMBINING ENCLOSING CIRCLE", "Enclosing circle"),
    ("\u20de", "COMBINING ENCLOSING SQUARE", "Enclosing square"),
    ("\u20df", "COMBINING ENCLOSING DIAMOND", "Enclosing diamond"),
    ("\u20e0", "COMBINING ENCLOSING CIRCLE BACKSLASH", "Prohibition sign"),
]

# --- LOGIC ---

LOGIC_BASIC = [
    ("\u2227", "LOGICAL AND", "Conjunction"),
    ("\u2228", "LOGICAL OR", "Disjunction"),
    ("\u00ac", "NOT SIGN", "Negation"),
    ("\u22bb", "XOR", "Exclusive or"),
    ("\u22bc", "NAND", "Not-and"),
    ("\u22bd", "NOR", "Not-or"),
    ("\u22a4", "DOWN TACK", "Tautology, true"),
    ("\u22a5", "UP TACK", "Contradiction, false, perpendicular"),
]

LOGIC_QUANTIFIERS = [
    ("\u2200", "FOR ALL", "Universal quantifier"),
    ("\u2203", "THERE EXISTS", "Existential quantifier"),
    ("\u2204", "THERE DOES NOT EXIST", "Negated existential"),
    ("\u2234", "THEREFORE", "Logical conclusion"),
    ("\u2235", "BECAUSE", "Logical reason"),
]

LOGIC_TURNSTILES = [
    ("\u22a2", "RIGHT TACK", "Proves, turnstile"),
    ("\u22a3", "LEFT TACK", "Reverse turnstile"),
    ("\u22a8", "TRUE", "Models, entails, satisfies"),
    ("\u22a9", "FORCES", "Forces (modal logic)"),
    ("\u22aa", "TRIPLE VERTICAL BAR RIGHT TURNSTILE", "Triple bar turnstile"),
    ("\u22ab", "DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE", "Double bar turnstile"),
    ("\u22ac", "DOES NOT PROVE", "Does not prove"),
    ("\u22ad", "NOT TRUE", "Does not model"),
    ("\u22ae", "DOES NOT FORCE", "Does not force"),
    ("\u22af", "NEGATED DOUBLE VERTICAL BAR DOUBLE RIGHT TURNSTILE", "Negated double bar"),
    ("\u27da", "LEFT AND RIGHT DOUBLE TURNSTILE", "Biconditional turnstile"),
    ("\u27db", "LEFT AND RIGHT TACK", "Left-right tack"),
]

# --- SET THEORY ---

SET_BASIC = [
    ("\u2205", "EMPTY SET", "Null set"),
    ("\u2208", "ELEMENT OF", "Is member of"),
    ("\u2209", "NOT AN ELEMENT OF", "Is not member of"),
    ("\u220b", "CONTAINS AS MEMBER", "Contains element"),
    ("\u220c", "DOES NOT CONTAIN AS MEMBER", "Does not contain"),
    ("\u2282", "SUBSET OF", "Proper subset"),
    ("\u2283", "SUPERSET OF", "Proper superset"),
    ("\u2284", "NOT A SUBSET OF", "Not a subset"),
    ("\u2285", "NOT A SUPERSET OF", "Not a superset"),
    ("\u2286", "SUBSET OF OR EQUAL TO", "Subset or equal"),
    ("\u2287", "SUPERSET OF OR EQUAL TO", "Superset or equal"),
    ("\u2288", "NEITHER A SUBSET OF NOR EQUAL TO", "Neither subset nor equal"),
    ("\u2289", "NEITHER A SUPERSET OF NOR EQUAL TO", "Neither superset nor equal"),
    ("\u228a", "SUBSET OF WITH NOT EQUAL TO", "Strict proper subset"),
    ("\u228b", "SUPERSET OF WITH NOT EQUAL TO", "Strict proper superset"),
]

SET_OPERATIONS = [
    ("\u222a", "UNION", "Set union"),
    ("\u2229", "INTERSECTION", "Set intersection"),
    ("\u2216", "SET MINUS", "Set difference"),
    ("\u228e", "MULTISET UNION", "Bag union"),
    ("\u228d", "DOUBLE INTERSECTION", "Multiset multiplication"),
    ("\u228c", "MULTISET", "Bag"),
    ("\u25b3", "WHITE UP-POINTING TRIANGLE", "Symmetric difference"),
    ("\u22c3", "N-ARY UNION", "Big union"),
    ("\u22c2", "N-ARY INTERSECTION", "Big intersection"),
]

SET_EXTENDED = [
    ("\u228f", "SQUARE IMAGE OF", "Domain restriction"),
    ("\u2290", "SQUARE ORIGINAL OF", "Range restriction"),
    ("\u2291", "SQUARE IMAGE OF OR EQUAL TO", "Square subset or equal"),
    ("\u2292", "SQUARE ORIGINAL OF OR EQUAL TO", "Square superset or equal"),
    ("\u2293", "SQUARE CAP", "Square intersection"),
    ("\u2294", "SQUARE CUP", "Square union, disjoint union"),
    ("\u22f2", "ELEMENT OF WITH LONG HORIZONTAL STROKE", "Element with stroke"),
    ("\u22f3", "ELEMENT OF WITH VERTICAL BAR AT END OF HORIZONTAL STROKE", "Element with bar"),
    ("\u22f4", "SMALL ELEMENT OF WITH VERTICAL BAR AT END OF HORIZONTAL STROKE", "Small element with bar"),
    ("\u22f5", "ELEMENT OF WITH DOT ABOVE", "Element with dot"),
    ("\u22f6", "ELEMENT OF WITH OVERBAR", "Element with overbar"),
    ("\u22f7", "SMALL ELEMENT OF WITH OVERBAR", "Small element with overbar"),
    ("\u22f8", "ELEMENT OF WITH UNDERBAR", "Element with underbar"),
    ("\u22f9", "ELEMENT OF WITH TWO HORIZONTAL STROKES", "Element with two strokes"),
    ("\u22fa", "CONTAINS WITH LONG HORIZONTAL STROKE", "Contains with stroke"),
    ("\u22fb", "CONTAINS WITH VERTICAL BAR AT END OF HORIZONTAL STROKE", "Contains with bar"),
    ("\u22fc", "SMALL CONTAINS WITH VERTICAL BAR AT END OF HORIZONTAL STROKE", "Small contains with bar"),
    ("\u22fd", "CONTAINS WITH OVERBAR", "Contains with overbar"),
    ("\u22fe", "SMALL CONTAINS WITH OVERBAR", "Small contains with overbar"),
]

# --- ALGEBRA ---

ALGEBRA_GROUP = [
    ("\u22b2", "NORMAL SUBGROUP OF", "Normal subgroup"),
    ("\u22b3", "CONTAINS AS NORMAL SUBGROUP", "Contains normal subgroup"),
    ("\u22b4", "NORMAL SUBGROUP OF OR EQUAL TO", "Normal subgroup or equal"),
    ("\u22b5", "CONTAINS AS NORMAL SUBGROUP OR EQUAL TO", "Contains normal or equal"),
    ("\u22ca", "RIGHT NORMAL FACTOR SEMIDIRECT PRODUCT", "Right semidirect product"),
    ("\u22c9", "LEFT NORMAL FACTOR SEMIDIRECT PRODUCT", "Left semidirect product"),
    ("\u22c8", "BOWTIE", "Natural join, relational algebra"),
    ("\u2240", "WREATH PRODUCT", "Wreath product"),
    ("\u22ea", "NOT NORMAL SUBGROUP OF", "Not normal subgroup"),
    ("\u22eb", "DOES NOT CONTAIN AS NORMAL SUBGROUP", "Not contains normal"),
    ("\u22ec", "NOT NORMAL SUBGROUP OF OR EQUAL TO", "Not normal or equal"),
    ("\u22ed", "DOES NOT CONTAIN AS NORMAL SUBGROUP OR EQUAL", "Not contains normal or equal"),
]

ALGEBRA_OPERATIONS = [
    ("\u22c6", "STAR OPERATOR", "Hodge star, convolution"),
    ("\u22c7", "DIVISION TIMES", "Division times"),
    ("\u29fa", "DOUBLE PLUS", "Double plus"),
    ("\u29fb", "TRIPLE PLUS", "Triple plus"),
]

CIRCLED_OPERATORS = [
    ("\u2295", "CIRCLED PLUS", "Direct sum, XOR"),
    ("\u2296", "CIRCLED MINUS", "Symmetric difference"),
    ("\u2297", "CIRCLED TIMES", "Tensor product, Kronecker product"),
    ("\u2298", "CIRCLED DIVISION SLASH", "Circled division"),
    ("\u2299", "CIRCLED DOT OPERATOR", "Scalar product, direct product"),
    ("\u229a", "CIRCLED RING OPERATOR", "Circled ring"),
    ("\u229b", "CIRCLED ASTERISK OPERATOR", "Circled asterisk"),
    ("\u229c", "CIRCLED EQUALS", "Circled equals"),
    ("\u229d", "CIRCLED DASH", "Circled dash"),
    ("\u29c0", "CIRCLED LESS-THAN", "Circled less than"),
    ("\u29c1", "CIRCLED GREATER-THAN", "Circled greater than"),
]

# --- ARROWS ---

ARROWS_BASIC = [
    ("\u2192", "RIGHTWARDS ARROW", "Right arrow, implies, function"),
    ("\u2190", "LEFTWARDS ARROW", "Left arrow, assignment"),
    ("\u2194", "LEFT RIGHT ARROW", "Biconditional, bijection"),
    ("\u2191", "UPWARDS ARROW", "Up arrow, exponentiation"),
    ("\u2193", "DOWNWARDS ARROW", "Down arrow"),
    ("\u2195", "UP DOWN ARROW", "Vertical bidirectional"),
    ("\u2197", "NORTH EAST ARROW", "Northeast diagonal"),
    ("\u2198", "SOUTH EAST ARROW", "Southeast diagonal"),
    ("\u2199", "SOUTH WEST ARROW", "Southwest diagonal"),
    ("\u2196", "NORTH WEST ARROW", "Northwest diagonal"),
]

ARROWS_DOUBLE = [
    ("\u21d2", "RIGHTWARDS DOUBLE ARROW", "Implies, logical consequence"),
    ("\u21d0", "LEFTWARDS DOUBLE ARROW", "Implied by, converse"),
    ("\u21d4", "LEFT RIGHT DOUBLE ARROW", "If and only if, biconditional"),
    ("\u21d1", "UPWARDS DOUBLE ARROW", "Double up"),
    ("\u21d3", "DOWNWARDS DOUBLE ARROW", "Double down"),
    ("\u21d5", "UP DOWN DOUBLE ARROW", "Vertical double arrow"),
    ("\u21d6", "NORTH WEST DOUBLE ARROW", "Double northwest"),
    ("\u21d7", "NORTH EAST DOUBLE ARROW", "Double northeast"),
    ("\u21d8", "SOUTH EAST DOUBLE ARROW", "Double southeast"),
    ("\u21d9", "SOUTH WEST DOUBLE ARROW", "Double southwest"),
]

ARROWS_LONG = [
    ("\u27f6", "LONG RIGHTWARDS ARROW", "Long right arrow"),
    ("\u27f5", "LONG LEFTWARDS ARROW", "Long left arrow"),
    ("\u27f7", "LONG LEFT RIGHT ARROW", "Long bidirectional"),
    ("\u27f9", "LONG RIGHTWARDS DOUBLE ARROW", "Long double right"),
    ("\u27f8", "LONG LEFTWARDS DOUBLE ARROW", "Long double left"),
    ("\u27fa", "LONG LEFT RIGHT DOUBLE ARROW", "Long double bidirectional"),
]

ARROWS_MAPPING = [
    ("\u21a6", "RIGHTWARDS ARROW FROM BAR", "Maps to"),
    ("\u21a4", "LEFTWARDS ARROW FROM BAR", "Maps from"),
    ("\u21a3", "RIGHTWARDS ARROW WITH TAIL", "Injection, monomorphism"),
    ("\u21a2", "LEFTWARDS ARROW WITH TAIL", "Left injection"),
    ("\u21a0", "RIGHTWARDS TWO HEADED ARROW", "Surjection, epimorphism"),
    ("\u219e", "LEFTWARDS TWO HEADED ARROW", "Left surjection"),
    ("\u21aa", "RIGHTWARDS ARROW WITH HOOK", "Inclusion, embedding"),
    ("\u21a9", "LEFTWARDS ARROW WITH HOOK", "Left inclusion"),
    ("\u21ac", "RIGHTWARDS ARROW WITH LOOP", "Arrow with loop"),
    ("\u21ab", "LEFTWARDS ARROW WITH LOOP", "Left arrow with loop"),
]

ARROWS_HARPOONS = [
    ("\u21c0", "RIGHTWARDS HARPOON WITH BARB UPWARDS", "Right harpoon up"),
    ("\u21c1", "RIGHTWARDS HARPOON WITH BARB DOWNWARDS", "Right harpoon down"),
    ("\u21bc", "LEFTWARDS HARPOON WITH BARB UPWARDS", "Left harpoon up"),
    ("\u21bd", "LEFTWARDS HARPOON WITH BARB DOWNWARDS", "Left harpoon down"),
    ("\u21cc", "RIGHTWARDS HARPOON OVER LEFTWARDS HARPOON", "Chemical equilibrium"),
    ("\u21cb", "LEFTWARDS HARPOON OVER RIGHTWARDS HARPOON", "Reverse equilibrium"),
    ("\u21bf", "UPWARDS HARPOON WITH BARB LEFTWARDS", "Up harpoon left"),
    ("\u21be", "UPWARDS HARPOON WITH BARB RIGHTWARDS", "Up harpoon right"),
    ("\u21c3", "DOWNWARDS HARPOON WITH BARB LEFTWARDS", "Down harpoon left"),
    ("\u21c2", "DOWNWARDS HARPOON WITH BARB RIGHTWARDS", "Down harpoon right"),
]

ARROWS_SPECIAL = [
    ("\u21af", "DOWNWARDS ZIGZAG ARROW", "Zigzag arrow, electromotive force"),
    ("\u27f2", "ANTICLOCKWISE GAPPED CIRCLE ARROW", "Anticlockwise circulation"),
    ("\u27f3", "CLOCKWISE GAPPED CIRCLE ARROW", "Clockwise circulation"),
    ("\u27f0", "UPWARDS QUADRUPLE ARROW", "Quadruple up arrow"),
    ("\u27f1", "DOWNWARDS QUADRUPLE ARROW", "Quadruple down arrow"),
    ("\u27f4", "RIGHT ARROW WITH CIRCLED PLUS", "Arrow with circled plus"),
]

# --- GEOMETRY ---

GEOMETRY_ANGLES = [
    ("\u221f", "RIGHT ANGLE", "90 degree angle"),
    ("\u2220", "ANGLE", "Plane angle"),
    ("\u2221", "MEASURED ANGLE", "Angle with arc"),
    ("\u2222", "SPHERICAL ANGLE", "Solid angle"),
    ("\u22be", "RIGHT ANGLE WITH ARC", "Right angle with arc"),
    ("\u22bf", "RIGHT TRIANGLE", "Right triangle"),
]

GEOMETRY_LINES = [
    ("\u27c2", "PERPENDICULAR", "Perpendicular to"),
    ("\u2225", "PARALLEL TO", "Parallel lines"),
    ("\u2226", "NOT PARALLEL TO", "Not parallel"),
    ("\u2312", "ARC", "Curved arc"),
    ("\u2313", "SEGMENT", "Line segment"),
]

GEOMETRY_RATIO = [
    ("\u2236", "RATIO", "Ratio, colon"),
    ("\u2237", "PROPORTION", "Proportional to"),
    ("\u2238", "DOT MINUS", "Dot minus"),
    ("\u2239", "EXCESS", "Excess, remainder"),
    ("\u223a", "GEOMETRIC PROPORTION", "Geometric proportion"),
    ("\u223b", "HOMOTHETIC", "Similarity, homothety"),
]

# --- ALPHABETS & NUMBER SYSTEMS ---

GREEK_LOWERCASE = [
    ("\u03b1", "GREEK SMALL LETTER ALPHA", "Alpha, significance level"),
    ("\u03b2", "GREEK SMALL LETTER BETA", "Beta, type II error"),
    ("\u03b3", "GREEK SMALL LETTER GAMMA", "Gamma, Euler constant"),
    ("\u03b4", "GREEK SMALL LETTER DELTA", "Delta, small change"),
    ("\u03b5", "GREEK SMALL LETTER EPSILON", "Epsilon, small quantity"),
    ("\u03b6", "GREEK SMALL LETTER ZETA", "Zeta, damping ratio"),
    ("\u03b7", "GREEK SMALL LETTER ETA", "Eta, efficiency"),
    ("\u03b8", "GREEK SMALL LETTER THETA", "Theta, angle parameter"),
    ("\u03b9", "GREEK SMALL LETTER IOTA", "Iota"),
    ("\u03ba", "GREEK SMALL LETTER KAPPA", "Kappa, curvature"),
    ("\u03bb", "GREEK SMALL LETTER LAMBDA", "Lambda, eigenvalue wavelength"),
    ("\u03bc", "GREEK SMALL LETTER MU", "Mu, mean micro"),
    ("\u03bd", "GREEK SMALL LETTER NU", "Nu, frequency"),
    ("\u03be", "GREEK SMALL LETTER XI", "Xi, random variable"),
    ("\u03bf", "GREEK SMALL LETTER OMICRON", "Omicron"),
    ("\u03c0", "GREEK SMALL LETTER PI", "Pi, 3.14159..."),
    ("\u03c1", "GREEK SMALL LETTER RHO", "Rho, density correlation"),
    ("\u03c3", "GREEK SMALL LETTER SIGMA", "Sigma, standard deviation"),
    ("\u03c2", "GREEK SMALL LETTER FINAL SIGMA", "Final sigma"),
    ("\u03c4", "GREEK SMALL LETTER TAU", "Tau, time constant torque"),
    ("\u03c5", "GREEK SMALL LETTER UPSILON", "Upsilon"),
    ("\u03c6", "GREEK SMALL LETTER PHI", "Phi, phase angle golden ratio"),
    ("\u03c7", "GREEK SMALL LETTER CHI", "Chi, chi-square"),
    ("\u03c8", "GREEK SMALL LETTER PSI", "Psi, wave function"),
    ("\u03c9", "GREEK SMALL LETTER OMEGA", "Omega, angular frequency"),
]

GREEK_UPPERCASE = [
    ("\u0393", "GREEK CAPITAL LETTER GAMMA", "Gamma function, group"),
    ("\u0394", "GREEK CAPITAL LETTER DELTA", "Delta, change difference"),
    ("\u0398", "GREEK CAPITAL LETTER THETA", "Theta, big-O notation"),
    ("\u039b", "GREEK CAPITAL LETTER LAMBDA", "Lambda, diagonal matrix"),
    ("\u039e", "GREEK CAPITAL LETTER XI", "Xi, cascade product"),
    ("\u03a0", "GREEK CAPITAL LETTER PI", "Pi, product operator"),
    ("\u03a3", "GREEK CAPITAL LETTER SIGMA", "Sigma, summation"),
    ("\u03a6", "GREEK CAPITAL LETTER PHI", "Phi, golden ratio flux"),
    ("\u03a8", "GREEK CAPITAL LETTER PSI", "Psi, wave function"),
    ("\u03a9", "GREEK CAPITAL LETTER OMEGA", "Omega, ohm sample space"),
]

GREEK_VARIANTS = [
    ("\u03d1", "GREEK THETA SYMBOL", "Variant theta"),
    ("\u03d5", "GREEK PHI SYMBOL", "Variant phi, straight phi"),
    ("\u03d6", "GREEK PI SYMBOL", "Variant pi, pomega"),
    ("\u03f1", "GREEK RHO SYMBOL", "Variant rho"),
    ("\u03f5", "GREEK LUNATE EPSILON SYMBOL", "Variant epsilon, lunate"),
    ("\u03f0", "GREEK KAPPA SYMBOL", "Variant kappa"),
]

HEBREW_LETTERS = [
    ("\u2135", "ALEF SYMBOL", "Aleph, cardinality of infinity"),
    ("\u2136", "BET SYMBOL", "Beth, cardinality"),
    ("\u2137", "GIMEL SYMBOL", "Gimel"),
    ("\u2138", "DALET SYMBOL", "Dalet"),
]

CYRILLIC_UPPERCASE = [
    ("\u0410", "CYRILLIC CAPITAL LETTER A", "Cyrillic A"),
    ("\u0411", "CYRILLIC CAPITAL LETTER BE", "Cyrillic Be"),
    ("\u0412", "CYRILLIC CAPITAL LETTER VE", "Cyrillic Ve"),
    ("\u0413", "CYRILLIC CAPITAL LETTER GHE", "Cyrillic Ghe"),
    ("\u0414", "CYRILLIC CAPITAL LETTER DE", "Cyrillic De"),
    ("\u0415", "CYRILLIC CAPITAL LETTER IE", "Cyrillic Ie"),
    ("\u0401", "CYRILLIC CAPITAL LETTER IO", "Cyrillic Io"),
    ("\u0416", "CYRILLIC CAPITAL LETTER ZHE", "Cyrillic Zhe"),
    ("\u0417", "CYRILLIC CAPITAL LETTER ZE", "Cyrillic Ze"),
    ("\u0418", "CYRILLIC CAPITAL LETTER I", "Cyrillic I"),
    ("\u0419", "CYRILLIC CAPITAL LETTER SHORT I", "Cyrillic Short I"),
    ("\u041a", "CYRILLIC CAPITAL LETTER KA", "Cyrillic Ka"),
    ("\u041b", "CYRILLIC CAPITAL LETTER EL", "Cyrillic El"),
    ("\u041c", "CYRILLIC CAPITAL LETTER EM", "Cyrillic Em"),
    ("\u041d", "CYRILLIC CAPITAL LETTER EN", "Cyrillic En"),
    ("\u041e", "CYRILLIC CAPITAL LETTER O", "Cyrillic O"),
    ("\u041f", "CYRILLIC CAPITAL LETTER PE", "Cyrillic Pe"),
    ("\u0420", "CYRILLIC CAPITAL LETTER ER", "Cyrillic Er"),
    ("\u0421", "CYRILLIC CAPITAL LETTER ES", "Cyrillic Es"),
    ("\u0422", "CYRILLIC CAPITAL LETTER TE", "Cyrillic Te"),
    ("\u0423", "CYRILLIC CAPITAL LETTER U", "Cyrillic U"),
    ("\u0424", "CYRILLIC CAPITAL LETTER EF", "Cyrillic Ef"),
    ("\u0425", "CYRILLIC CAPITAL LETTER HA", "Cyrillic Ha"),
    ("\u0426", "CYRILLIC CAPITAL LETTER TSE", "Cyrillic Tse"),
    ("\u0427", "CYRILLIC CAPITAL LETTER CHE", "Cyrillic Che"),
    ("\u0428", "CYRILLIC CAPITAL LETTER SHA", "Cyrillic Sha"),
    ("\u0429", "CYRILLIC CAPITAL LETTER SHCHA", "Cyrillic Shcha"),
    ("\u042a", "CYRILLIC CAPITAL LETTER HARD SIGN", "Cyrillic Hard Sign"),
    ("\u042b", "CYRILLIC CAPITAL LETTER YERU", "Cyrillic Yeru"),
    ("\u042c", "CYRILLIC CAPITAL LETTER SOFT SIGN", "Cyrillic Soft Sign"),
    ("\u042d", "CYRILLIC CAPITAL LETTER E", "Cyrillic E"),
    ("\u042e", "CYRILLIC CAPITAL LETTER YU", "Cyrillic Yu"),
    ("\u042f", "CYRILLIC CAPITAL LETTER YA", "Cyrillic Ya"),
]

CYRILLIC_LOWERCASE = [
    ("\u0430", "CYRILLIC SMALL LETTER A", "Cyrillic a"),
    ("\u0431", "CYRILLIC SMALL LETTER BE", "Cyrillic be"),
    ("\u0432", "CYRILLIC SMALL LETTER VE", "Cyrillic ve"),
    ("\u0433", "CYRILLIC SMALL LETTER GHE", "Cyrillic ghe"),
    ("\u0434", "CYRILLIC SMALL LETTER DE", "Cyrillic de"),
    ("\u0435", "CYRILLIC SMALL LETTER IE", "Cyrillic ie"),
    ("\u0451", "CYRILLIC SMALL LETTER IO", "Cyrillic io"),
    ("\u0436", "CYRILLIC SMALL LETTER ZHE", "Cyrillic zhe"),
    ("\u0437", "CYRILLIC SMALL LETTER ZE", "Cyrillic ze"),
    ("\u0438", "CYRILLIC SMALL LETTER I", "Cyrillic i"),
    ("\u0439", "CYRILLIC SMALL LETTER SHORT I", "Cyrillic short i"),
    ("\u043a", "CYRILLIC SMALL LETTER KA", "Cyrillic ka"),
    ("\u043b", "CYRILLIC SMALL LETTER EL", "Cyrillic el"),
    ("\u043c", "CYRILLIC SMALL LETTER EM", "Cyrillic em"),
    ("\u043d", "CYRILLIC SMALL LETTER EN", "Cyrillic en"),
    ("\u043e", "CYRILLIC SMALL LETTER O", "Cyrillic o"),
    ("\u043f", "CYRILLIC SMALL LETTER PE", "Cyrillic pe"),
    ("\u0440", "CYRILLIC SMALL LETTER ER", "Cyrillic er"),
    ("\u0441", "CYRILLIC SMALL LETTER ES", "Cyrillic es"),
    ("\u0442", "CYRILLIC SMALL LETTER TE", "Cyrillic te"),
    ("\u0443", "CYRILLIC SMALL LETTER U", "Cyrillic u"),
    ("\u0444", "CYRILLIC SMALL LETTER EF", "Cyrillic ef"),
    ("\u0445", "CYRILLIC SMALL LETTER HA", "Cyrillic ha"),
    ("\u0446", "CYRILLIC SMALL LETTER TSE", "Cyrillic tse"),
    ("\u0447", "CYRILLIC SMALL LETTER CHE", "Cyrillic che"),
    ("\u0448", "CYRILLIC SMALL LETTER SHA", "Cyrillic sha"),
    ("\u0449", "CYRILLIC SMALL LETTER SHCHA", "Cyrillic shcha"),
    ("\u044a", "CYRILLIC SMALL LETTER HARD SIGN", "Cyrillic hard sign"),
    ("\u044b", "CYRILLIC SMALL LETTER YERU", "Cyrillic yeru"),
    ("\u044c", "CYRILLIC SMALL LETTER SOFT SIGN", "Cyrillic soft sign"),
    ("\u044d", "CYRILLIC SMALL LETTER E", "Cyrillic e"),
    ("\u044e", "CYRILLIC SMALL LETTER YU", "Cyrillic yu"),
    ("\u044f", "CYRILLIC SMALL LETTER YA", "Cyrillic ya"),
]

CYRILLIC_EXTENDED = [
    ("\u0402", "CYRILLIC CAPITAL LETTER DJE", "Serbian Dje"),
    ("\u0403", "CYRILLIC CAPITAL LETTER GJE", "Macedonian Gje"),
    ("\u0404", "CYRILLIC CAPITAL LETTER UKRAINIAN IE", "Ukrainian Ie"),
    ("\u0405", "CYRILLIC CAPITAL LETTER DZE", "Macedonian Dze"),
    ("\u0406", "CYRILLIC CAPITAL LETTER BYELORUSSIAN-UKRAINIAN I", "Dotted I"),
    ("\u0407", "CYRILLIC CAPITAL LETTER YI", "Ukrainian Yi"),
    ("\u0408", "CYRILLIC CAPITAL LETTER JE", "Serbian Je"),
    ("\u0409", "CYRILLIC CAPITAL LETTER LJE", "Serbian Lje"),
    ("\u040a", "CYRILLIC CAPITAL LETTER NJE", "Serbian Nje"),
    ("\u040b", "CYRILLIC CAPITAL LETTER TSHE", "Serbian Tshe"),
    ("\u040c", "CYRILLIC CAPITAL LETTER KJE", "Macedonian Kje"),
    ("\u040e", "CYRILLIC CAPITAL LETTER SHORT U", "Belarusian Short U"),
    ("\u040f", "CYRILLIC CAPITAL LETTER DZHE", "Serbian Dzhe"),
    ("\u0490", "CYRILLIC CAPITAL LETTER GHE WITH UPTURN", "Ukrainian Ghe"),
    ("\u0452", "CYRILLIC SMALL LETTER DJE", "Serbian dje"),
    ("\u0453", "CYRILLIC SMALL LETTER GJE", "Macedonian gje"),
    ("\u0454", "CYRILLIC SMALL LETTER UKRAINIAN IE", "Ukrainian ie"),
    ("\u0455", "CYRILLIC SMALL LETTER DZE", "Macedonian dze"),
    ("\u0456", "CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I", "Dotted i"),
    ("\u0457", "CYRILLIC SMALL LETTER YI", "Ukrainian yi"),
    ("\u0458", "CYRILLIC SMALL LETTER JE", "Serbian je"),
    ("\u0459", "CYRILLIC SMALL LETTER LJE", "Serbian lje"),
    ("\u045a", "CYRILLIC SMALL LETTER NJE", "Serbian nje"),
    ("\u045b", "CYRILLIC SMALL LETTER TSHE", "Serbian tshe"),
    ("\u045c", "CYRILLIC SMALL LETTER KJE", "Macedonian kje"),
    ("\u045e", "CYRILLIC SMALL LETTER SHORT U", "Belarusian short u"),
    ("\u045f", "CYRILLIC SMALL LETTER DZHE", "Serbian dzhe"),
    ("\u0491", "CYRILLIC SMALL LETTER GHE WITH UPTURN", "Ukrainian ghe"),
]

NUMBER_SETS = [
    ("\u2102", "DOUBLE-STRUCK CAPITAL C", "Complex numbers"),
    ("\u210d", "DOUBLE-STRUCK CAPITAL H", "Quaternions, Hamiltonian"),
    ("\u2115", "DOUBLE-STRUCK CAPITAL N", "Natural numbers"),
    ("\u2119", "DOUBLE-STRUCK CAPITAL P", "Primes, projective space"),
    ("\u211a", "DOUBLE-STRUCK CAPITAL Q", "Rational numbers"),
    ("\u211d", "DOUBLE-STRUCK CAPITAL R", "Real numbers"),
    ("\u2124", "DOUBLE-STRUCK CAPITAL Z", "Integers"),
]

MATH_SCRIPT_LETTERS = [
    ("\u212c", "SCRIPT CAPITAL B", "Bernoulli number"),
    ("\u2130", "SCRIPT CAPITAL E", "Electromotive force"),
    ("\u2131", "SCRIPT CAPITAL F", "Fourier transform"),
    ("\u210b", "SCRIPT CAPITAL H", "Hamiltonian, Hilbert space"),
    ("\u2110", "SCRIPT CAPITAL I", "Ideal"),
    ("\u2112", "SCRIPT CAPITAL L", "Laplace transform, Lagrangian"),
    ("\u2133", "SCRIPT CAPITAL M", "M-matrix"),
    ("\u211b", "SCRIPT CAPITAL R", "Riemann integral"),
    ("\u2113", "SCRIPT SMALL L", "Litre, length"),
    ("\u2118", "SCRIPT CAPITAL P", "Weierstrass P function"),
]

MATH_CONSTANTS = [
    ("\u2147", "DOUBLE-STRUCK ITALIC SMALL E", "Euler's number e"),
    ("\u2148", "DOUBLE-STRUCK ITALIC SMALL I", "Imaginary unit i"),
    ("\u2149", "DOUBLE-STRUCK ITALIC SMALL J", "Imaginary unit j (engineering)"),
    ("\u210f", "PLANCK CONSTANT OVER TWO PI", "Reduced Planck constant, h-bar"),
    ("\u2111", "BLACK-LETTER CAPITAL I", "Imaginary part"),
    ("\u211c", "BLACK-LETTER CAPITAL R", "Real part"),
]

# --- NUMBERS & SCRIPTS ---

FRACTIONS = [
    ("\u00bd", "VULGAR FRACTION ONE HALF", "1/2"),
    ("\u2153", "VULGAR FRACTION ONE THIRD", "1/3"),
    ("\u2154", "VULGAR FRACTION TWO THIRDS", "2/3"),
    ("\u00bc", "VULGAR FRACTION ONE QUARTER", "1/4"),
    ("\u00be", "VULGAR FRACTION THREE QUARTERS", "3/4"),
    ("\u2155", "VULGAR FRACTION ONE FIFTH", "1/5"),
    ("\u2156", "VULGAR FRACTION TWO FIFTHS", "2/5"),
    ("\u2157", "VULGAR FRACTION THREE FIFTHS", "3/5"),
    ("\u2158", "VULGAR FRACTION FOUR FIFTHS", "4/5"),
    ("\u2159", "VULGAR FRACTION ONE SIXTH", "1/6"),
    ("\u215a", "VULGAR FRACTION FIVE SIXTHS", "5/6"),
    ("\u215b", "VULGAR FRACTION ONE EIGHTH", "1/8"),
    ("\u215c", "VULGAR FRACTION THREE EIGHTHS", "3/8"),
    ("\u215d", "VULGAR FRACTION FIVE EIGHTHS", "5/8"),
    ("\u215e", "VULGAR FRACTION SEVEN EIGHTHS", "7/8"),
]

SUPERSCRIPTS = [
    # numbers 0-9
    ("\u2070", "SUPERSCRIPT ZERO", "Exponent 0"),
    ("\u00b9", "SUPERSCRIPT ONE", "Exponent 1"),
    ("\u00b2", "SUPERSCRIPT TWO", "Squared, exponent 2"),
    ("\u00b3", "SUPERSCRIPT THREE", "Cubed, exponent 3"),
    ("\u2074", "SUPERSCRIPT FOUR", "Exponent 4"),
    ("\u2075", "SUPERSCRIPT FIVE", "Exponent 5"),
    ("\u2076", "SUPERSCRIPT SIX", "Exponent 6"),
    ("\u2077", "SUPERSCRIPT SEVEN", "Exponent 7"),
    ("\u2078", "SUPERSCRIPT EIGHT", "Exponent 8"),
    ("\u2079", "SUPERSCRIPT NINE", "Exponent 9"),
    # lowercase latin a-z (q not available in unicode)
    ("\u1d43", "MODIFIER LETTER SMALL A", "Superscript a"),
    ("\u1d47", "MODIFIER LETTER SMALL B", "Superscript b"),
    ("\u1d9c", "MODIFIER LETTER SMALL C", "Superscript c"),
    ("\u1d48", "MODIFIER LETTER SMALL D", "Superscript d"),
    ("\u1d49", "MODIFIER LETTER SMALL E", "Superscript e"),
    ("\u1da0", "MODIFIER LETTER SMALL F", "Superscript f"),
    ("\u1d4d", "MODIFIER LETTER SMALL G", "Superscript g"),
    ("\u02b0", "MODIFIER LETTER SMALL H", "Superscript h"),
    ("\u2071", "SUPERSCRIPT LATIN SMALL LETTER I", "Superscript i"),
    ("\u02b2", "MODIFIER LETTER SMALL J", "Superscript j"),
    ("\u1d4f", "MODIFIER LETTER SMALL K", "Superscript k"),
    ("\u02e1", "MODIFIER LETTER SMALL L", "Superscript l"),
    ("\u1d50", "MODIFIER LETTER SMALL M", "Superscript m"),
    ("\u207f", "SUPERSCRIPT LATIN SMALL LETTER N", "Superscript n"),
    ("\u1d52", "MODIFIER LETTER SMALL O", "Superscript o"),
    ("\u1d56", "MODIFIER LETTER SMALL P", "Superscript p"),
    ("\u02b3", "MODIFIER LETTER SMALL R", "Superscript r"),
    ("\u02e2", "MODIFIER LETTER SMALL S", "Superscript s"),
    ("\u1d57", "MODIFIER LETTER SMALL T", "Superscript t"),
    ("\u1d58", "MODIFIER LETTER SMALL U", "Superscript u"),
    ("\u1d5b", "MODIFIER LETTER SMALL V", "Superscript v"),
    ("\u02b7", "MODIFIER LETTER SMALL W", "Superscript w"),
    ("\u02e3", "MODIFIER LETTER SMALL X", "Superscript x"),
    ("\u02b8", "MODIFIER LETTER SMALL Y", "Superscript y"),
    ("\u1dbb", "MODIFIER LETTER SMALL Z", "Superscript z"),
    # lowercase greek (limited availability in unicode)
    ("\u1d5d", "MODIFIER LETTER SMALL BETA", "Superscript beta"),
    ("\u1d5e", "MODIFIER LETTER SMALL GREEK GAMMA", "Superscript gamma"),
    ("\u1d5f", "MODIFIER LETTER SMALL DELTA", "Superscript delta"),
    ("\u1d60", "MODIFIER LETTER SMALL GREEK PHI", "Superscript phi"),
    ("\u1d61", "MODIFIER LETTER SMALL CHI", "Superscript chi"),
    # operators
    ("\u207a", "SUPERSCRIPT PLUS SIGN", "Positive exponent"),
    ("\u207b", "SUPERSCRIPT MINUS", "Negative exponent"),
    ("\u207c", "SUPERSCRIPT EQUALS SIGN", "Superscript equals"),
    ("\u207d", "SUPERSCRIPT LEFT PARENTHESIS", "Superscript open paren"),
    ("\u207e", "SUPERSCRIPT RIGHT PARENTHESIS", "Superscript close paren"),
]

SUBSCRIPTS = [
    # numbers 0-9
    ("\u2080", "SUBSCRIPT ZERO", "Index 0"),
    ("\u2081", "SUBSCRIPT ONE", "Index 1"),
    ("\u2082", "SUBSCRIPT TWO", "Index 2"),
    ("\u2083", "SUBSCRIPT THREE", "Index 3"),
    ("\u2084", "SUBSCRIPT FOUR", "Index 4"),
    ("\u2085", "SUBSCRIPT FIVE", "Index 5"),
    ("\u2086", "SUBSCRIPT SIX", "Index 6"),
    ("\u2087", "SUBSCRIPT SEVEN", "Index 7"),
    ("\u2088", "SUBSCRIPT EIGHT", "Index 8"),
    ("\u2089", "SUBSCRIPT NINE", "Index 9"),
    # lowercase latin (limited availability - b,c,d,f,g,q,w,y,z not in unicode)
    ("\u2090", "LATIN SUBSCRIPT SMALL LETTER A", "Subscript a"),
    ("\u2091", "LATIN SUBSCRIPT SMALL LETTER E", "Subscript e"),
    ("\u2095", "LATIN SUBSCRIPT SMALL LETTER H", "Subscript h"),
    ("\u1d62", "LATIN SUBSCRIPT SMALL LETTER I", "Subscript i"),
    ("\u2c7c", "LATIN SUBSCRIPT SMALL LETTER J", "Subscript j"),
    ("\u2096", "LATIN SUBSCRIPT SMALL LETTER K", "Subscript k"),
    ("\u2097", "LATIN SUBSCRIPT SMALL LETTER L", "Subscript l"),
    ("\u2098", "LATIN SUBSCRIPT SMALL LETTER M", "Subscript m"),
    ("\u2099", "LATIN SUBSCRIPT SMALL LETTER N", "Subscript n"),
    ("\u2092", "LATIN SUBSCRIPT SMALL LETTER O", "Subscript o"),
    ("\u209a", "LATIN SUBSCRIPT SMALL LETTER P", "Subscript p"),
    ("\u1d63", "LATIN SUBSCRIPT SMALL LETTER R", "Subscript r"),
    ("\u209b", "LATIN SUBSCRIPT SMALL LETTER S", "Subscript s"),
    ("\u209c", "LATIN SUBSCRIPT SMALL LETTER T", "Subscript t"),
    ("\u1d64", "LATIN SUBSCRIPT SMALL LETTER U", "Subscript u"),
    ("\u1d65", "LATIN SUBSCRIPT SMALL LETTER V", "Subscript v"),
    ("\u2093", "LATIN SUBSCRIPT SMALL LETTER X", "Subscript x"),
    # lowercase greek (limited availability in unicode)
    ("\u1d66", "GREEK SUBSCRIPT SMALL LETTER BETA", "Subscript beta"),
    ("\u1d67", "GREEK SUBSCRIPT SMALL LETTER GAMMA", "Subscript gamma"),
    ("\u1d68", "GREEK SUBSCRIPT SMALL LETTER RHO", "Subscript rho"),
    ("\u1d69", "GREEK SUBSCRIPT SMALL LETTER PHI", "Subscript phi"),
    ("\u1d6a", "GREEK SUBSCRIPT SMALL LETTER CHI", "Subscript chi"),
    # operators
    ("\u208a", "SUBSCRIPT PLUS SIGN", "Subscript plus"),
    ("\u208b", "SUBSCRIPT MINUS", "Subscript minus"),
    ("\u208c", "SUBSCRIPT EQUALS SIGN", "Subscript equals"),
    ("\u208d", "SUBSCRIPT LEFT PARENTHESIS", "Subscript open paren"),
    ("\u208e", "SUBSCRIPT RIGHT PARENTHESIS", "Subscript close paren"),
]

# --- BRACKETS & DELIMITERS ---

BRACKETS_FLOOR_CEILING = [
    ("\u2308", "LEFT CEILING", "Ceiling function open"),
    ("\u2309", "RIGHT CEILING", "Ceiling function close"),
    ("\u230a", "LEFT FLOOR", "Floor function open"),
    ("\u230b", "RIGHT FLOOR", "Floor function close"),
    ("\u27ec", "WHITE LEFT TORTOISE SHELL BRACKET", "White tortoise left"),
    ("\u27ed", "WHITE RIGHT TORTOISE SHELL BRACKET", "White tortoise right"),
    ("\u27ee", "MATHEMATICAL LEFT FLATTENED PARENTHESIS", "Flattened paren left"),
    ("\u27ef", "MATHEMATICAL RIGHT FLATTENED PARENTHESIS", "Flattened paren right"),
]

BRACKETS_ANGLE = [
    ("\u27e8", "MATHEMATICAL LEFT ANGLE BRACKET", "Bra-ket notation, inner product"),
    ("\u27e9", "MATHEMATICAL RIGHT ANGLE BRACKET", "Ket, inner product"),
    ("\u27ea", "MATHEMATICAL LEFT DOUBLE ANGLE BRACKET", "Double angle left"),
    ("\u27eb", "MATHEMATICAL RIGHT DOUBLE ANGLE BRACKET", "Double angle right"),
    ("\u2991", "LEFT ANGLE BRACKET WITH DOT", "Angle with dot left"),
    ("\u2992", "RIGHT ANGLE BRACKET WITH DOT", "Angle with dot right"),
    ("\u2993", "LEFT ARC LESS-THAN BRACKET", "Arc less-than left"),
    ("\u2994", "RIGHT ARC GREATER-THAN BRACKET", "Arc greater-than right"),
    ("\u2995", "DOUBLE LEFT ARC GREATER-THAN BRACKET", "Double arc left"),
    ("\u2996", "DOUBLE RIGHT ARC LESS-THAN BRACKET", "Double arc right"),
    ("\u29fc", "LEFT-POINTING CURVED ANGLE BRACKET", "Curved angle left"),
    ("\u29fd", "RIGHT-POINTING CURVED ANGLE BRACKET", "Curved angle right"),
]

BRACKETS_SQUARE_DOUBLE = [
    ("\u27e6", "MATHEMATICAL LEFT WHITE SQUARE BRACKET", "Double bracket left"),
    ("\u27e7", "MATHEMATICAL RIGHT WHITE SQUARE BRACKET", "Double bracket right"),
    ("\u2983", "LEFT WHITE CURLY BRACKET", "White curly left"),
    ("\u2984", "RIGHT WHITE CURLY BRACKET", "White curly right"),
    ("\u2985", "LEFT WHITE PARENTHESIS", "White paren left"),
    ("\u2986", "RIGHT WHITE PARENTHESIS", "White paren right"),
    ("\u2987", "Z NOTATION LEFT IMAGE BRACKET", "Z notation image left"),
    ("\u2988", "Z NOTATION RIGHT IMAGE BRACKET", "Z notation image right"),
    ("\u2989", "Z NOTATION LEFT BINDING BRACKET", "Z notation binding left"),
    ("\u298a", "Z NOTATION RIGHT BINDING BRACKET", "Z notation binding right"),
    ("\u298b", "LEFT SQUARE BRACKET WITH UNDERBAR", "Bracket underbar left"),
    ("\u298c", "RIGHT SQUARE BRACKET WITH UNDERBAR", "Bracket underbar right"),
    ("\u298d", "LEFT SQUARE BRACKET WITH TICK IN TOP CORNER", "Bracket tick top left"),
    ("\u298e", "RIGHT SQUARE BRACKET WITH TICK IN BOTTOM CORNER", "Bracket tick bottom right"),
    ("\u298f", "LEFT SQUARE BRACKET WITH TICK IN BOTTOM CORNER", "Bracket tick bottom left"),
    ("\u2990", "RIGHT SQUARE BRACKET WITH TICK IN TOP CORNER", "Bracket tick top right"),
    ("\u2997", "LEFT BLACK TORTOISE SHELL BRACKET", "Tortoise shell left"),
    ("\u2998", "RIGHT BLACK TORTOISE SHELL BRACKET", "Tortoise shell right"),
]

ELLIPSES = [
    ("\u22ee", "VERTICAL ELLIPSIS", "Vertical dots"),
    ("\u22ef", "MIDLINE HORIZONTAL ELLIPSIS", "Horizontal dots, cdots"),
    ("\u22f0", "UP RIGHT DIAGONAL ELLIPSIS", "Diagonal up ellipsis"),
    ("\u22f1", "DOWN RIGHT DIAGONAL ELLIPSIS", "Diagonal down ellipsis"),
]

# --- UNITS & MEASUREMENTS ---

UNITS_MEASUREMENTS = [
    ("\u00b0", "DEGREE SIGN", "Degrees, temperature angle"),
    ("\u212b", "ANGSTROM SIGN", "Angstrom, 10⁻¹⁰ meters"),
    ("\u2103", "DEGREE CELSIUS", "Degrees Celsius"),
    ("\u2109", "DEGREE FAHRENHEIT", "Degrees Fahrenheit"),
    ("\u03a9", "GREEK CAPITAL LETTER OMEGA", "Ohm, resistance"),
    ("\u2127", "INVERTED OHM SIGN", "Mho, conductance, siemens"),
    ("\u2300", "DIAMETER SIGN", "Diameter"),
    ("\u2116", "NUMERO SIGN", "Number sign"),
    ("\u212e", "ESTIMATED SYMBOL", "Estimated weight"),
]

# --- GEOMETRIC SHAPES ---

SHAPES_CIRCLES = [
    ("\u25ef", "LARGE CIRCLE", "Large white circle"),
    ("\u25cb", "WHITE CIRCLE", "White circle"),
    ("\u25cf", "BLACK CIRCLE", "Black circle, bullet"),
    ("\u25d0", "CIRCLE WITH LEFT HALF BLACK", "Left half black circle"),
    ("\u25d1", "CIRCLE WITH RIGHT HALF BLACK", "Right half black circle"),
    ("\u25d2", "CIRCLE WITH LOWER HALF BLACK", "Lower half black circle"),
    ("\u25d3", "CIRCLE WITH UPPER HALF BLACK", "Upper half black circle"),
    ("\u25d4", "CIRCLE WITH UPPER RIGHT QUADRANT BLACK", "Upper right quadrant"),
    ("\u25d5", "CIRCLE WITH ALL BUT UPPER LEFT QUADRANT BLACK", "Three quadrants black"),
    ("\u25d6", "LEFT HALF BLACK CIRCLE", "Left half circle"),
    ("\u25d7", "RIGHT HALF BLACK CIRCLE", "Right half circle"),
    ("\u25e0", "UPPER HALF CIRCLE", "Upper arc"),
    ("\u25e1", "LOWER HALF CIRCLE", "Lower arc"),
    ("\u2981", "Z NOTATION SPOT", "Spot, filled circle"),
    ("\u25e6", "WHITE BULLET", "White bullet, ring"),
    ("\u29c2", "CIRCLE WITH SMALL CIRCLE TO THE RIGHT", "Circle with circle"),
    ("\u29c3", "CIRCLE WITH TWO HORIZONTAL STROKES TO THE RIGHT", "Circle with strokes"),
    ("\u29ec", "CIRCLE WITH DOWNWARDS ARROW BELOW", "Circle down arrow"),
    ("\u29ed", "BLACK CIRCLE WITH DOWNWARDS ARROW", "Black circle arrow"),
]

SHAPES_SQUARES = [
    ("\u25a1", "WHITE SQUARE", "White square"),
    ("\u25a0", "BLACK SQUARE", "Black square"),
    ("\u25a2", "WHITE SQUARE WITH ROUNDED CORNERS", "Rounded square"),
    ("\u25a3", "WHITE SQUARE CONTAINING BLACK SMALL SQUARE", "Square in square"),
    ("\u25a4", "SQUARE WITH HORIZONTAL FILL", "Horizontal fill"),
    ("\u25a5", "SQUARE WITH VERTICAL FILL", "Vertical fill"),
    ("\u25a6", "SQUARE WITH ORTHOGONAL CROSSHATCH FILL", "Crosshatch fill"),
    ("\u25a7", "SQUARE WITH UPPER LEFT TO LOWER RIGHT FILL", "Diagonal fill UL-LR"),
    ("\u25a8", "SQUARE WITH UPPER RIGHT TO LOWER LEFT FILL", "Diagonal fill UR-LL"),
    ("\u25a9", "SQUARE WITH DIAGONAL CROSSHATCH FILL", "Diagonal crosshatch"),
    ("\u25aa", "BLACK SMALL SQUARE", "Small black square"),
    ("\u25ab", "WHITE SMALL SQUARE", "Small white square"),
    ("\u25e7", "SQUARE WITH LEFT HALF BLACK", "Left half square"),
    ("\u25e8", "SQUARE WITH RIGHT HALF BLACK", "Right half square"),
    ("\u25e9", "SQUARE WITH UPPER LEFT DIAGONAL HALF BLACK", "Upper left diagonal"),
    ("\u25ea", "SQUARE WITH LOWER RIGHT DIAGONAL HALF BLACK", "Lower right diagonal"),
    ("\u25eb", "WHITE SQUARE WITH VERTICAL BISECTING LINE", "Bisected square"),
    ("\u29c4", "SQUARED RISING DIAGONAL SLASH", "Rising diagonal"),
    ("\u29c5", "SQUARED FALLING DIAGONAL SLASH", "Falling diagonal"),
    ("\u29c6", "SQUARED ASTERISK", "Squared asterisk"),
    ("\u29c7", "SQUARED SMALL CIRCLE", "Squared circle"),
    ("\u29c8", "SQUARED SQUARE", "Squared square"),
    ("\u29c9", "TWO JOINED SQUARES", "Joined squares"),
    ("\u29e0", "SQUARE WITH CONTOURED OUTLINE", "Contoured square"),
    ("\u29ee", "ERROR-BARRED WHITE SQUARE", "Error bar square"),
    ("\u29ef", "ERROR-BARRED BLACK SQUARE", "Error bar black square"),
]

SHAPES_RECTANGLES = [
    ("\u25ac", "BLACK RECTANGLE", "Black rectangle"),
    ("\u25ad", "WHITE RECTANGLE", "White rectangle"),
    ("\u25ae", "BLACK VERTICAL RECTANGLE", "Vertical black rect"),
    ("\u25af", "WHITE VERTICAL RECTANGLE", "Vertical white rect"),
]

SHAPES_TRIANGLES = [
    ("\u25b3", "WHITE UP-POINTING TRIANGLE", "Up triangle, delta"),
    ("\u25b2", "BLACK UP-POINTING TRIANGLE", "Black up triangle"),
    ("\u25b7", "WHITE RIGHT-POINTING TRIANGLE", "Right triangle, play"),
    ("\u25b6", "BLACK RIGHT-POINTING TRIANGLE", "Black right triangle"),
    ("\u25bd", "WHITE DOWN-POINTING TRIANGLE", "Down triangle, nabla"),
    ("\u25bc", "BLACK DOWN-POINTING TRIANGLE", "Black down triangle"),
    ("\u25c1", "WHITE LEFT-POINTING TRIANGLE", "Left triangle"),
    ("\u25c0", "BLACK LEFT-POINTING TRIANGLE", "Black left triangle"),
    ("\u25e2", "BLACK LOWER RIGHT TRIANGLE", "Lower right triangle"),
    ("\u25e3", "BLACK LOWER LEFT TRIANGLE", "Lower left triangle"),
    ("\u25e4", "BLACK UPPER LEFT TRIANGLE", "Upper left triangle"),
    ("\u25e5", "BLACK UPPER RIGHT TRIANGLE", "Upper right triangle"),
    ("\u25ec", "WHITE UP-POINTING TRIANGLE WITH DOT", "Triangle with dot"),
    ("\u25ed", "UP-POINTING TRIANGLE WITH LEFT HALF BLACK", "Left half triangle"),
    ("\u25ee", "UP-POINTING TRIANGLE WITH RIGHT HALF BLACK", "Right half triangle"),
    ("\u29ca", "TRIANGLE WITH DOT ABOVE", "Triangle dot above"),
    ("\u29cb", "TRIANGLE WITH UNDERBAR", "Triangle underbar"),
    ("\u29cc", "S IN TRIANGLE", "S in triangle"),
    ("\u29cd", "TRIANGLE WITH SERIFS AT BOTTOM", "Serif triangle"),
    ("\u29ce", "RIGHT TRIANGLE ABOVE LEFT TRIANGLE", "Stacked triangles"),
    ("\u29cf", "LEFT TRIANGLE BESIDE VERTICAL BAR", "Triangle bar left"),
    ("\u29d0", "VERTICAL BAR BESIDE RIGHT TRIANGLE", "Bar triangle right"),
    ("\u29e8", "DOWN-POINTING TRIANGLE WITH LEFT HALF BLACK", "Down left half"),
    ("\u29e9", "DOWN-POINTING TRIANGLE WITH RIGHT HALF BLACK", "Down right half"),
]

SHAPES_DIAMONDS = [
    ("\u25c7", "WHITE DIAMOND", "White diamond"),
    ("\u25c6", "BLACK DIAMOND", "Black diamond"),
    ("\u25c8", "WHITE DIAMOND CONTAINING BLACK SMALL DIAMOND", "Diamond in diamond"),
    ("\u27d0", "WHITE DIAMOND WITH CENTRED DOT", "Diamond with dot"),
    ("\u27e0", "LOZENGE DIVIDED BY HORIZONTAL RULE", "Divided lozenge"),
    ("\u27e1", "WHITE CONCAVE-SIDED DIAMOND", "Concave diamond"),
    ("\u27e2", "WHITE CONCAVE-SIDED DIAMOND WITH LEFTWARDS TICK", "Concave tick left"),
    ("\u27e3", "WHITE CONCAVE-SIDED DIAMOND WITH RIGHTWARDS TICK", "Concave tick right"),
    ("\u29ea", "BLACK DIAMOND WITH DOWN ARROW", "Diamond with arrow"),
    ("\u29eb", "BLACK LOZENGE", "Black lozenge"),
]

SHAPES_STARS_MISC = [
    ("\u2605", "BLACK STAR", "Black star, rating"),
    ("\u2606", "WHITE STAR", "White star, outline"),
    ("\u2713", "CHECK MARK", "Check mark, correct"),
    ("\u2717", "BALLOT X", "Ballot X, wrong"),
    ("\u2715", "MULTIPLICATION X", "Multiplication X"),
    ("\u2716", "HEAVY MULTIPLICATION X", "Heavy multiplication"),
    ("\u2718", "HEAVY BALLOT X", "Heavy ballot X"),
    ("\u271a", "HEAVY GREEK CROSS", "Heavy cross"),
    ("\u271b", "OPEN CENTRE CROSS", "Open center cross"),
    ("\u271c", "HEAVY OPEN CENTRE CROSS", "Heavy open cross"),
    ("\u29d1", "BOWTIE WITH LEFT HALF BLACK", "Left bowtie"),
    ("\u29d2", "BOWTIE WITH RIGHT HALF BLACK", "Right bowtie"),
    ("\u29d3", "BLACK BOWTIE", "Black bowtie"),
    ("\u29d4", "TIMES WITH LEFT HALF BLACK", "Left times"),
    ("\u29d5", "TIMES WITH RIGHT HALF BLACK", "Right times"),
    ("\u29d6", "WHITE HOURGLASS", "White hourglass"),
    ("\u29d7", "BLACK HOURGLASS", "Black hourglass"),
]

# --- MISCELLANEOUS ---

DATABASE_RELATIONAL = [
    ("\u27d5", "LEFT OUTER JOIN", "Left outer join"),
    ("\u27d6", "RIGHT OUTER JOIN", "Right outer join"),
    ("\u27d7", "FULL OUTER JOIN", "Full outer join"),
]

MISC_MATHEMATICAL = [
    ("\u223e", "INVERTED LAZY S", "Inverted lazy S, sine integral"),
    ("\u223f", "SINE WAVE", "Alternating current, sine wave"),
    ("\u29dc", "INCOMPLETE INFINITY", "Partial infinity"),
    ("\u29dd", "TIE OVER INFINITY", "Tie over infinity"),
    ("\u29de", "INFINITY NEGATED WITH VERTICAL BAR", "Negated infinity"),
    ("\u29df", "DOUBLE-ENDED MULTIMAP", "Double multimap"),
    ("\u29e1", "INCREASES AS", "Increases as"),
    ("\u29e2", "SHUFFLE PRODUCT", "Shuffle product"),
    ("\u29e3", "EQUALS SIGN AND SLANTED PARALLEL", "Equals with parallel"),
    ("\u29e4", "EQUALS SIGN AND SLANTED PARALLEL WITH TILDE ABOVE", "Equals parallel tilde"),
    ("\u29e5", "IDENTICAL TO AND SLANTED PARALLEL", "Identical with parallel"),
    ("\u29e6", "GLEICH STARK", "Gleich stark, equally strong"),
    ("\u29e7", "THERMODYNAMIC", "Thermodynamic"),
]

MISC_TECHNICAL = [
    ("\u2310", "REVERSED NOT SIGN", "Reversed not"),
    ("\u2311", "SQUARE LOZENGE", "Square lozenge"),
    ("\u2315", "TELEPHONE RECORDER", "Telephone recorder"),
    ("\u2316", "POSITION INDICATOR", "Position indicator"),
    ("\u2317", "VIEWDATA SQUARE", "Viewdata square"),
    ("\u2318", "PLACE OF INTEREST SIGN", "Command key, Apple"),
    ("\u2319", "TURNED NOT SIGN", "Turned not sign"),
    ("\u27dc", "LEFT MULTIMAP", "Left multimap"),
    ("\u27dd", "LONG RIGHT TACK", "Long right tack"),
    ("\u27de", "LONG LEFT TACK", "Long left tack"),
    ("\u27df", "UP TACK WITH CIRCLE ABOVE", "Up tack with circle"),
    ("\u27e4", "WHITE SQUARE WITH LEFTWARDS TICK", "Square left tick"),
    ("\u27e5", "WHITE SQUARE WITH RIGHTWARDS TICK", "Square right tick"),
    ("\u27d1", "AND WITH DOT", "And with dot"),
    ("\u27d2", "ELEMENT OF OPENING UPWARDS", "Element opening up"),
    ("\u27d3", "LOWER RIGHT CORNER WITH DOT", "Corner with dot LR"),
    ("\u27d4", "UPPER LEFT CORNER WITH DOT", "Corner with dot UL"),
    ("\u27d8", "LARGE UP TACK", "Large up tack"),
    ("\u27d9", "LARGE DOWN TACK", "Large down tack"),
    ("\u2980", "TRIPLE VERTICAL BAR DELIMITER", "Triple bar"),
    ("\u2982", "Z NOTATION TYPE COLON", "Type colon"),
]

# master dictionary organizing all groups
SYMBOL_GROUPS = {
    # core mathematics
    "Basic Arithmetic": BASIC_ARITHMETIC,
    "Equality & Inequality": EQUALITY_INEQUALITY,
    "Equivalence & Approximation": EQUIVALENCE_APPROXIMATION,
    "Definition & Assignment": DEFINITION_ASSIGNMENT,
    "Order Relations": ORDER_RELATIONS,
    "Roots & Powers": ROOTS_POWERS,
    # calculus & analysis
    "Differential Calculus": CALCULUS_DIFFERENTIAL,
    "Integrals": CALCULUS_INTEGRALS,
    "Summation & Products": CALCULUS_SUMMATION,
    # statistics & probability
    "Statistics & Probability": STATISTICS_PROBABILITY,
    "Means (Bar)": MEANS_BAR_ABOVE,
    "Estimates (Hat)": ESTIMATES_HAT,
    "Derivatives (Dot)": DERIVATIVES_DOT,
    "Vectors (Arrow)": VECTORS_ARROW,
    "Transforms (Tilde)": TILDE_TRANSFORM,
    "Tensors (Double Bar)": DOUBLE_BAR_TENSOR,
    "Other Combinations": COMBINATIONS_OTHER,
    "Combining Marks": COMBINING_DIACRITICALS,
    # logic
    "Logic Operators": LOGIC_BASIC,
    "Quantifiers": LOGIC_QUANTIFIERS,
    "Turnstiles & Proof": LOGIC_TURNSTILES,
    # set theory
    "Set Theory Basic": SET_BASIC,
    "Set Operations": SET_OPERATIONS,
    "Set Extended": SET_EXTENDED,
    # algebra
    "Group Theory": ALGEBRA_GROUP,
    "Algebra Operations": ALGEBRA_OPERATIONS,
    "Circled Operators": CIRCLED_OPERATORS,
    # arrows
    "Arrows Basic": ARROWS_BASIC,
    "Arrows Double": ARROWS_DOUBLE,
    "Arrows Long": ARROWS_LONG,
    "Arrows Mapping": ARROWS_MAPPING,
    "Arrows Harpoons": ARROWS_HARPOONS,
    "Arrows Special": ARROWS_SPECIAL,
    # geometry
    "Geometry Angles": GEOMETRY_ANGLES,
    "Geometry Lines": GEOMETRY_LINES,
    "Geometry Ratio": GEOMETRY_RATIO,
    # alphabets & number systems
    "Greek Lowercase": GREEK_LOWERCASE,
    "Greek Uppercase": GREEK_UPPERCASE,
    "Greek Variants": GREEK_VARIANTS,
    "Hebrew Letters": HEBREW_LETTERS,
    "Cyrillic Uppercase": CYRILLIC_UPPERCASE,
    "Cyrillic Lowercase": CYRILLIC_LOWERCASE,
    "Cyrillic Extended": CYRILLIC_EXTENDED,
    "Number Sets": NUMBER_SETS,
    "Script Letters": MATH_SCRIPT_LETTERS,
    "Math Constants": MATH_CONSTANTS,
    # numbers & scripts
    "Fractions": FRACTIONS,
    "Superscripts": SUPERSCRIPTS,
    "Subscripts": SUBSCRIPTS,
    # brackets & delimiters
    "Floor & Ceiling": BRACKETS_FLOOR_CEILING,
    "Angle Brackets": BRACKETS_ANGLE,
    "Square & Double Brackets": BRACKETS_SQUARE_DOUBLE,
    "Ellipses": ELLIPSES,
    # units & measurements
    "Units & Measurements": UNITS_MEASUREMENTS,
    # geometric shapes
    "Circles": SHAPES_CIRCLES,
    "Squares": SHAPES_SQUARES,
    "Rectangles": SHAPES_RECTANGLES,
    "Triangles": SHAPES_TRIANGLES,
    "Diamonds & Lozenges": SHAPES_DIAMONDS,
    "Stars & Misc Shapes": SHAPES_STARS_MISC,
    # miscellaneous
    "Database & Relational": DATABASE_RELATIONAL,
    "Misc Mathematical": MISC_MATHEMATICAL,
    "Misc Technical": MISC_TECHNICAL,
}

# flatten all symbols for search
# format: (symbol, name, description, group_name)
ALL_SYMBOLS: List[Tuple[str, str, str, str]] = []
for group_name, symbols in SYMBOL_GROUPS.items():
    for symbol, name, description in symbols:
        ALL_SYMBOLS.append((symbol, name, description, group_name))


def search_score(query: str, text: str) -> int:
    # scoring: 100 exact match, 80 prefix, 50 substring, 0 no match
    query = query.lower()
    text = text.lower()
    words = text.replace("-", " ").replace("/", " ").split()

    for word in words:
        if word == query:
            return 100
        if word.startswith(query):
            return 80

    if query in text:
        return 50

    return 0


class SymbolsDialog(CenteredDialog):
    def __init__(
        self,
        master,
        on_insert: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        self.on_insert = on_insert
        self._search_results_frame: Optional[ctk.CTkFrame] = None
        self._search_job_id: Optional[str] = None
        self._search_index: Dict[str, List[Tuple[str, str, str]]] = {}

        # collapsible group state - only expanded groups render symbols
        self._group_headers: List[ctk.CTkButton] = []
        self._group_containers: List[ctk.CTkFrame] = []
        self._group_grids: Dict[str, ctk.CTkFrame] = {}
        self._expanded_groups: set = set()
        self._is_searching: bool = False

        super().__init__(
            master,
            title="Math Symbols",
            width=650,
            height=700,
            **kwargs
        )

    def _build_content(self) -> None:
        label_font = ctk.CTkFont(size=14)
        section_font = ctk.CTkFont(size=13, weight="bold")
        # catrinity has excellent unicode coverage (80,000+ characters)
        symbol_font = ctk.CTkFont(family="Catrinity", size=24)
        btn_font = ctk.CTkFont(size=14)

        # search box at the top
        search_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        search_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            search_frame,
            text="Search:",
            font=label_font
        ).pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            width=460,
            height=36,
            font=label_font,
            placeholder_text="Type to search symbols by name..."
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_search_change_debounced)

        bind_entry_shortcuts(self, self.search_entry)

        # scrollable frame for symbol groups
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.content_frame,
            width=540,
            height=400,
            fg_color="transparent"
        )
        self.scroll_frame.pack(fill="both", expand=True, pady=(0, 10))

        self._bind_mouse_wheel_optimized(self.scroll_frame)

        self._section_font = section_font
        self._symbol_font = symbol_font

        # create only headers - no symbol buttons yet (fast!)
        for group_name, symbols in SYMBOL_GROUPS.items():
            self._create_collapsible_group(group_name, symbols)

        # build search index in background
        self.after_idle(self._build_search_index)

        # text entry for collected symbols
        entry_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(5, 10))

        ctk.CTkLabel(
            entry_frame,
            text="Selected:",
            font=label_font
        ).pack(side="left", padx=(0, 10))

        self.symbol_entry = ctk.CTkEntry(
            entry_frame,
            width=380,
            height=36,
            font=ctk.CTkFont(size=16)
        )
        self.symbol_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        bind_entry_shortcuts(self, self.symbol_entry)

        clear_btn = ctk.CTkButton(
            entry_frame,
            text="Clear",
            width=60,
            height=36,
            font=btn_font,
            fg_color="transparent",
            border_width=1,
            text_color=("gray30", "gray70"),
            command=self._on_clear
        )
        clear_btn.pack(side="right")

        # buttons
        btn_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 0))

        close_btn = ctk.CTkButton(
            btn_frame,
            text="Close",
            width=100,
            height=38,
            font=btn_font,
            fg_color="transparent",
            border_width=1,
            text_color=("gray30", "gray70"),
            command=self._on_close
        )
        close_btn.pack(side="left")

        insert_btn = ctk.CTkButton(
            btn_frame,
            text="Insert",
            width=100,
            height=38,
            font=btn_font,
            command=self._on_insert
        )
        insert_btn.pack(side="right")

    def _bind_mouse_wheel_optimized(self, scroll_frame: ctk.CTkScrollableFrame) -> None:
        canvas = scroll_frame._parent_canvas

        def can_scroll(direction: int) -> bool:
            """Check if scrolling in the given direction is allowed."""
            top, bottom = canvas.yview()
            # if all content is visible, no scrolling needed
            if top == 0.0 and bottom == 1.0:
                return False
            # check boundaries based on direction
            if direction < 0:  # scrolling up
                return top > 0.0
            else:  # scrolling down
                return bottom < 1.0

        def _on_mousewheel(event):
            direction = -1 if event.delta > 0 else 1
            if can_scroll(direction):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _on_mousewheel_linux(event):
            if event.num == 4:  # scroll up
                if can_scroll(-1):
                    canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # scroll down
                if can_scroll(1):
                    canvas.yview_scroll(1, "units")
            return "break"

        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", _on_mousewheel_linux)
        canvas.bind("<Button-5>", _on_mousewheel_linux)
        self.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        self.bind_all("<Button-4>", _on_mousewheel_linux, add="+")
        self.bind_all("<Button-5>", _on_mousewheel_linux, add="+")

    def _build_search_index(self) -> None:
        for symbol, name, description, group in ALL_SYMBOLS:
            # index by name, description, and group words
            search_text = f"{name} {description} {group}"
            words = search_text.lower().replace("-", " ").replace("/", " ").split()
            for word in words:
                if word not in self._search_index:
                    self._search_index[word] = []
                self._search_index[word].append((symbol, name, description, group))

    def _on_search_change_debounced(self, event=None) -> None:
        if self._search_job_id:
            self.after_cancel(self._search_job_id)
        self._search_job_id = self.after(SEARCH_DEBOUNCE_MS, self._do_search)

    def _create_collapsible_group(self, group_name: str, symbols: list) -> None:
        # container for header + grid
        container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        container.pack(fill="x", pady=(2, 0))

        # clickable header - shows symbol count
        header = ctk.CTkButton(
            container,
            text=f"▶ {group_name} ({len(symbols)})",
            font=self._section_font,
            anchor="w",
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray20", "gray80"),
            height=28,
            command=lambda g=group_name, s=symbols, c=container: self._toggle_group(g, s, c)
        )
        header.pack(fill="x", padx=5)

        self._group_headers.append(header)
        self._group_containers.append(container)
        # grid created only on expand - not now!

    def _toggle_group(self, group_name: str, symbols: list, container: ctk.CTkFrame) -> None:
        if group_name in self._expanded_groups:
            # collapse - destroy grid
            self._expanded_groups.discard(group_name)
            if group_name in self._group_grids:
                self._group_grids[group_name].destroy()
                del self._group_grids[group_name]
            # update header arrow
            for header in self._group_headers:
                if group_name in header.cget("text"):
                    header.configure(text=f"▶ {group_name} ({len(symbols)})")
                    break
        else:
            # expand - create grid now
            self._expanded_groups.add(group_name)
            grid_frame = ctk.CTkFrame(container, fg_color=("gray90", "gray17"))
            grid_frame.pack(fill="x", padx=5, pady=(0, 5))
            self._populate_grid(grid_frame, symbols, self._symbol_font)
            self._group_grids[group_name] = grid_frame
            # update header arrow
            for header in self._group_headers:
                if group_name in header.cget("text"):
                    header.configure(text=f"▼ {group_name} ({len(symbols)})")
                    break

    def _populate_grid(
        self,
        grid_frame: ctk.CTkFrame,
        symbols: list,
        symbol_font: ctk.CTkFont
    ) -> None:
        for child in grid_frame.winfo_children():
            child.destroy()

        cols = 10
        row = 0
        col = 0

        for item in symbols:
            # handle both (symbol, name, desc) and (symbol, desc) for search results
            if len(item) == 3:
                symbol, name, description = item
                tooltip = f"{symbol}  {name}\n{description}"
            else:
                symbol, description = item
                tooltip = f"{symbol}  {description}"

            btn = ctk.CTkButton(
                grid_frame,
                text=symbol,
                width=48,
                height=48,
                font=symbol_font,
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                text_color=("gray10", "gray90"),
                command=lambda s=symbol: self._add_symbol(s)
            )
            btn.grid(row=row, column=col, padx=2, pady=2)

            self._bind_tooltip(btn, tooltip)

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _do_search(self) -> None:
        self._search_job_id = None
        query = self.search_entry.get().strip()

        if not query:
            self._is_searching = False
            self._show_all_groups()
            return

        self._is_searching = True
        self._hide_all_groups()
        self._show_search_results(query)

    def _hide_all_groups(self) -> None:
        for container in self._group_containers:
            container.pack_forget()

    def _show_all_groups(self) -> None:
        if self._search_results_frame:
            self._search_results_frame.pack_forget()

        for container in self._group_containers:
            container.pack(fill="x", pady=(2, 0))

        self.scroll_frame.update_idletasks()
        self.scroll_frame._parent_canvas.yview_moveto(0)

    def _show_search_results(self, query: str) -> None:
        query_lower = query.lower()

        # use index for fast lookup when available
        if self._search_index:
            seen = set()
            scored_matches = []

            # check index for matching words
            for word in self._search_index:
                if word.startswith(query_lower) or query_lower in word:
                    for symbol, name, description, group in self._search_index[word]:
                        if symbol not in seen:
                            seen.add(symbol)
                            score = search_score(query, f"{name} {description} {group}")
                            scored_matches.append((score, symbol, name, description))
        else:
            # fallback to full scan if index not built yet
            scored_matches = []
            for symbol, name, description, group in ALL_SYMBOLS:
                search_text = f"{name} {description} {group}"
                score = search_score(query, search_text)
                if score > 0:
                    scored_matches.append((score, symbol, name, description))

        scored_matches.sort(key=lambda x: (-x[0], x[3]))
        matches = [(sym, name, desc) for _, sym, name, desc in scored_matches[:100]]

        if not self._search_results_frame:
            self._search_results_frame = ctk.CTkFrame(
                self.scroll_frame,
                fg_color="transparent"
            )
        else:
            self._search_results_frame.pack_forget()

        for child in self._search_results_frame.winfo_children():
            child.destroy()

        if matches:
            result_text = f"Search Results ({len(matches)} found)"
            if len(scored_matches) > 100:
                result_text = f"Search Results (showing 100 of {len(scored_matches)})"

            ctk.CTkLabel(
                self._search_results_frame,
                text=result_text,
                font=self._section_font,
                anchor="w"
            ).pack(fill="x", pady=(10, 5), padx=5)

            grid_frame = ctk.CTkFrame(
                self._search_results_frame,
                fg_color=("gray90", "gray17")
            )
            grid_frame.pack(fill="x", padx=5, pady=(0, 5))

            self._populate_grid(grid_frame, matches, self._symbol_font)
        else:
            ctk.CTkLabel(
                self._search_results_frame,
                text="No symbols found",
                font=self._section_font,
                text_color=("gray50", "gray60"),
                anchor="w"
            ).pack(fill="x", pady=(20, 5), padx=5)

        self._search_results_frame.pack(fill="x")

        self.scroll_frame.update_idletasks()
        self.scroll_frame._parent_canvas.yview_moveto(0)

    def _bind_tooltip(self, widget: ctk.CTkButton, text: str) -> None:
        tooltip = None

        def show_tooltip(event):
            nonlocal tooltip
            if tooltip:
                return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 5

            tooltip = ctk.CTkToplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            tooltip.attributes("-topmost", True)

            label = ctk.CTkLabel(
                tooltip,
                text=text,
                font=ctk.CTkFont(family="DejaVu Sans", size=15),
                fg_color=("gray85", "gray25"),
                corner_radius=6,
                padx=12,
                pady=8
            )
            label.pack()

        def hide_tooltip(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def _add_symbol(self, symbol: str) -> None:
        current = self.symbol_entry.get()
        self.symbol_entry.delete(0, "end")
        self.symbol_entry.insert(0, current + symbol)

    def _on_clear(self) -> None:
        self.symbol_entry.delete(0, "end")

    def _on_insert(self) -> None:
        symbols = self.symbol_entry.get()
        if symbols and self.on_insert:
            self.on_insert(symbols)
        self._on_close()
