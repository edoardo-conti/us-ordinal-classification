import tensorflow as tf
import numpy as np
from sklearn.metrics import confusion_matrix

'''
OBD Metrics (WIP)
'''

target_class = np.ones((4, 4 - 1), dtype=np.float32)
target_class[np.triu_indices(4, 0, 4 - 1)] = 0.0

def from_obdout_to_labels(obd_y_pred):
	# Calculate pairwise distances between y_pred and target_class using Euclidean distance
	distances = tf.norm(tf.expand_dims(obd_y_pred, 1) - target_class, axis=2, ord='euclidean')
    
	# Find the index of the minimum distance as the predicted label
	labels = tf.argmin(distances, axis=1)

	return labels

def ccr(y_true, y_pred):
	# predit labels for each sample from network output
	y_pred = from_obdout_to_labels(y_pred)

	# Find the true labels
	y_true = tf.argmax(y_true, axis=-1) 

	# Check for correct predictions
	correct = tf.equal(y_true, y_pred)

	# Calculate the Correct Classification Rate
	ccr_value = tf.reduce_mean(tf.cast(correct, tf.float32))

	return ccr_value

def ms(y_true, y_pred):
	# !NOT SURE IF WORKING!
	# predit labels for each sample from network output
	y_pred = from_obdout_to_labels(y_pred)

	# Find the true labels
	y_true = tf.argmax(y_true, axis=-1) 

	# Calculate confusion matrix
	#cm = confusion_matrix(y_true, y_pred).astype(float)
	cm = tf.math.confusion_matrix(y_true, y_pred, num_classes=4, dtype=tf.float32)
	
	# Calculate sum of true positives (TP) for each class
	#sum_byclass = np.sum(cm, axis=1).astype(float)
	sum_byclass = tf.reduce_sum(cm, axis=1)

	# Calculate sensitivities (TP / sum by class)
	#sensitivities = np.diag(cm) / sum_byclass
	sensitivities = tf.linalg.diag_part(cm) / sum_byclass

	# Find the minimum sensitivity
	ms = tf.reduce_min(sensitivities)

	return ms

def mae(y_true, y_pred):
	# predit labels for each sample from network output
	y_pred = from_obdout_to_labels(y_pred)

	# Find the true labels
	y_true = tf.argmax(y_true, axis=-1) 

	y_true = tf.convert_to_tensor(y_true, dtype=tf.int64)
	y_pred = tf.convert_to_tensor(y_pred, dtype=tf.int64)

	absolute_errors = tf.abs(y_true - y_pred)
	mean_absolute_error = tf.reduce_sum(absolute_errors) / tf.cast(tf.shape(y_true)[0], dtype=tf.int64)

	return mean_absolute_error

def accuracy_oneoff(y_true, y_pred):
	# predit labels for each sample from network output
	y_pred = from_obdout_to_labels(y_pred)

	#if y_true.shape[0] > 1:
	# Find the true labels
	y_true = tf.argmax(y_true, axis=-1) 

	conf_mat = tf.math.confusion_matrix(y_true, y_pred, num_classes=4, dtype=tf.float32)
	n = tf.shape(conf_mat)[0]

	#mask = tf.eye(n) + tf.eye(n, delta=1) + tf.eye(n, delta=-1)
	mask = tf.linalg.diag(tf.ones(n)) + tf.linalg.diag(tf.ones(n - 1), k=1) + tf.linalg.diag(tf.ones(n - 1), k=-1)
	correct = mask * conf_mat
	
	accuracy_1off = tf.reduce_sum(correct) / tf.reduce_sum(conf_mat)

	return accuracy_1off


'''
ORDINAL
'''
def histogram(ratings, min_rating=None, max_rating=None):
	"""
	Returns the counts of each type of rating that a rater made
	"""
	if min_rating is None:
		min_rating = min(ratings)
	if max_rating is None:
		max_rating = max(ratings)
	num_ratings = int(max_rating - min_rating + 1)
	hist_ratings = [0 for x in range(num_ratings)]
	for r in ratings:
		hist_ratings[r - min_rating] += 1

	return hist_ratings

def _confusion_matrix(rater_a, rater_b, min_rating=None, max_rating=None):
	"""
	Returns the confusion matrix between rater's ratings
	"""
	assert (len(rater_a) == len(rater_b))
	if min_rating is None:
		min_rating = min(rater_a + rater_b)
	if max_rating is None:
		max_rating = max(rater_a + rater_b)
	num_ratings = int(max_rating - min_rating + 1)
	conf_mat = [[0 for i in range(num_ratings)]
				for j in range(num_ratings)]
	for a, b in zip(rater_a, rater_b):
		conf_mat[a - min_rating][b - min_rating] += 1
	return conf_mat


def np_quadratic_weighted_kappa(rater_a, rater_b, min_rating=None, max_rating=None):
	"""
	Calculates the quadratic weighted kappa
	quadratic_weighted_kappa calculates the quadratic weighted kappa
	value, which is a measure of inter-rater agreement between two raters
	that provide discrete numeric ratings.  Potential values range from -1
	(representing complete disagreement) to 1 (representing complete
	agreement).  A kappa value of 0 is expected if all agreement is due to
	chance.

	quadratic_weighted_kappa(rater_a, rater_b), where rater_a and rater_b
	each correspond to a list of integer ratings.  These lists must have the
	same length.

	The ratings should be integers, and it is assumed that they contain
	the complete range of possible ratings.

	quadratic_weighted_kappa(X, min_rating, max_rating), where min_rating
	is the minimum possible rating, and max_rating is the maximum possible
	rating
	"""

	# Change values lower than min_rating to min_rating and values
	# higher than max_rating to max_rating.
	rater_a = np.clip(rater_a, min_rating, max_rating)
	rater_b = np.clip(rater_b, min_rating, max_rating)

	rater_a = np.round(rater_a).astype(int).ravel()
	rater_a[~np.isfinite(rater_a)] = 0
	rater_b = np.round(rater_b).astype(int).ravel()
	rater_b[~np.isfinite(rater_b)] = 0

	assert (len(rater_a) == len(rater_b))
	# Get min_rating and max_rating from raters if they are None.
	if min_rating is None:
		min_rating = min(min(rater_a), min(rater_b))
	if max_rating is None:
		max_rating = max(max(rater_a), max(rater_b))
	conf_mat = _confusion_matrix(rater_a, rater_b,
								min_rating, max_rating)

	num_ratings = len(conf_mat)
	num_scored_items = float(len(rater_a))

	hist_rater_a = histogram(rater_a, min_rating, max_rating)
	hist_rater_b = histogram(rater_b, min_rating, max_rating)

	numerator = 0.0
	denominator = 0.0

	for i in range(num_ratings):
		for j in range(num_ratings):
			expected_count = (hist_rater_a[i] * hist_rater_b[j]
							  / num_scored_items)
			d = pow(i - j, 2.0) / pow(num_ratings - 1, 2.0)
			numerator += d * conf_mat[i][j] / num_scored_items
			denominator += d * expected_count / num_scored_items

	return 1.0 - numerator / denominator