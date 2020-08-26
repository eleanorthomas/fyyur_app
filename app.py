#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
from datetime import datetime
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship("Show", backref="Venue")

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship("Show", backref="Artist")

class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime)
    artist_id = db.Column(db.Integer, db.ForeignKey("Artist.id"))
    venue_id = db.Column(db.Integer, db.ForeignKey("Venue.id"))

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []
  for city, state in db.session.query(Venue.city, Venue.state).distinct():
    city_state = dict()
    city_state['city'] = city
    city_state['state'] = state

    venues_list = []
    venues = Venue.query.filter_by(city=city, state=state).all()
    for venue in venues:
      venue_dict = dict()
      venue_dict['id'] = venue.id
      venue_dict['name'] = venue.name
      venue_dict['num_upcoming_shows'] = 0

      shows = Show.query.filter_by(venue_id=venue.id).all()
      for show in shows:
        if show.start_time >= datetime.today():
          venue_dict['num_upcoming_shows'] += 1

      venues_list.append(venue_dict)

    city_state['venues'] = venues_list

    data.append(city_state)

  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # search on artists with partial string search, case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"

  search_term=request.form.get('search_term', '')

  response = dict()
  response['count'] = 0
  response['data'] = []

  for venue in Venue.query.filter(Venue.name.ilike('%'+search_term+'%')).all():
    response['count'] += 1
    res_dict = dict()
    res_dict['id'] = venue.id
    res_dict['name'] = venue.name
    res_dict['num_upcoming_shows'] = 0
    shows = Show.query.filter_by(venue_id=venue.id).all()
    for show in shows:
      if show.start_time >= datetime.today():
        res_dict['num_upcoming_shows'] += 1

    response['data'].append(res_dict)

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue = Venue.query.get(venue_id)

  data = dict()
  data['id'] = venue.id
  data['name'] = venue.name
  data['genres'] = venue.genres.split(', ')
  data['address'] = venue.address
  data['city'] = venue.city
  data['state'] = venue.state
  data['phone'] = venue.phone
  data['website'] = venue.website
  data['facebook_link'] = venue.facebook_link
  data['seeking_talent'] = venue.seeking_talent
  data['seeking_description'] = venue.seeking_description
  data['image_link'] = venue.image_link

  data['past_shows'] = []
  data['upcoming_shows'] = []
  data['past_shows_count'] = 0
  data['upcoming_shows_count'] = 0

  shows = Show.query.filter_by(venue_id=venue_id).all()
  for show in shows:
    show_dict = dict()
    show_dict['artist_id'] = show.artist_id

    artist = Artist.query.get(show.artist_id)
    show_dict['artist_name'] = artist.name
    show_dict['artist_image_link'] = artist.image_link
    show_dict['start_time'] = str(show.start_time)

    if show.start_time >= datetime.today():
      data['upcoming_shows_count'] += 1
      data['upcoming_shows'].append(show_dict)
    else:
      data['past_shows_count'] += 1
      data['past_shows'].append(show_dict)

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    address = request.form['address']
    phone = request.form['phone']
    genres = ', '.join(request.form.getlist('genres'))
    website = request.form['website']
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    seeking_talent = 'seeking_talent' in request.form.items()
    seeking_description = request.form['seeking_description']

    venue = Venue(
      name=name,
      city=city,
      state=state,
      address=address,
      phone=phone,
      genres=genres,
      website=website,
      image_link=image_link,
      facebook_link=facebook_link,
      seeking_talent=seeking_talent,
      seeking_description=seeking_description
    )
    db.session.add(venue)
    db.session.commit()
  except:
    e = str(sys.exc_info()[0]) + ': ' + str(sys.exc_info()[1])
    error = True
    db.session.rollback()
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed. ' + e)
  else:
    flash('Venue ' + request.form['name']+ ' was successfully listed!')
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = []
  for artist in Artist.query.all():
    artist_dict = dict()
    artist_dict['id'] = artist.id
    artist_dict['name'] = artist.name
    data.append(artist_dict)

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # search on artists with partial string search, case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  search_term=request.form.get('search_term', '')

  response = dict()
  response['count'] = 0
  response['data'] = []

  for artist in Artist.query.filter(Artist.name.ilike('%'+search_term+'%')).all():
    response['count'] += 1
    res_dict = dict()
    res_dict['id'] = artist.id
    res_dict['name'] = artist.name
    res_dict['num_upcoming_shows'] = 0
    shows = Show.query.filter_by(artist_id=artist.id).all()
    for show in shows:
      if show.start_time >= datetime.today():
        res_dict['num_upcoming_shows'] += 1

    response['data'].append(res_dict)

  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  artist = Artist.query.get(artist_id)

  data = dict()
  data['id'] = artist.id
  data['name'] = artist.name
  data['genres'] = artist.genres.split(', ')
  data['city'] = artist.city
  data['state'] = artist.state
  data['phone'] = artist.phone
  data['website'] = artist.website
  data['facebook_link'] = artist.facebook_link
  data['seeking_venue'] = artist.seeking_venue
  data['seeking_description'] = artist.seeking_description
  data['image_link'] = artist.image_link

  data['past_shows'] = []
  data['upcoming_shows'] = []
  data['past_shows_count'] = 0
  data['upcoming_shows_count'] = 0

  shows = Show.query.filter_by(artist_id=artist_id).all()
  for show in shows:
    show_dict = dict()
    show_dict['venue_id'] = show.venue_id

    venue = Venue.query.get(show.venue_id)
    show_dict['venue_name'] = venue.name
    show_dict['venue_image_link'] = venue.image_link
    show_dict['start_time'] = str(show.start_time)

    if show.start_time >= datetime.today():
      data['upcoming_shows_count'] += 1
      data['upcoming_shows'].append(show_dict)
    else:
      data['past_shows_count'] += 1
      data['past_shows'].append(show_dict)

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()

  artist_obj = Artist.query.get(artist_id)

  artist = dict()
  artist['id'] = artist_obj.id
  artist['name'] = artist_obj.name
  artist['genres'] = artist_obj.genres.split(', ')
  artist['city'] = artist_obj.city
  artist['state'] = artist_obj.state
  artist['phone'] = artist_obj.phone
  artist['website'] = artist_obj.website
  artist['facebook_link'] = artist_obj.facebook_link
  artist['seeking_venue'] = artist_obj.seeking_venue
  artist['seeking_description'] = artist_obj.seeking_description
  artist['image_link'] = artist_obj.image_link

  # TODO: populate form with values from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()

  venue_obj = Venue.query.get(venue_id)

  venue = dict()
  venue['id'] = venue_obj.id
  venue['name'] = venue_obj.name
  venue['genres'] = venue_obj.genres.split(', ')
  venue['address'] = venue_obj.address
  venue['city'] = venue_obj.city
  venue['state'] = venue_obj.state
  venue['phone'] = venue_obj.phone
  venue['website'] = venue_obj.website
  venue['facebook_link'] = venue_obj.facebook_link
  venue['seeking_talent'] = venue_obj.seeking_talent
  venue['seeking_description'] = venue_obj.seeking_description
  venue['image_link'] = venue_obj.image_link

  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  error = False
  try:
    name = request.form['name']
    city = request.form['city']
    state = request.form['state']
    phone = request.form['phone']
    genres = ', '.join(request.form.getlist('genres'))
    website = request.form['website']
    image_link = request.form['image_link']
    facebook_link = request.form['facebook_link']
    seeking_venue = 'seeking_venue' in request.form.items()
    seeking_description = request.form['seeking_description']

    artist = Artist(
      name=name,
      city=city,
      state=state,
      phone=phone,
      genres="",
      website=website,
      image_link=image_link,
      facebook_link=facebook_link,
      seeking_venue=seeking_venue,
      seeking_description=seeking_description
    )

    db.session.add(artist)
    db.session.commit()
  except:
    e = str(sys.exc_info()[0]) + ': ' + str(sys.exc_info()[1])
    error = True
    db.session.rollback()
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed. ' + e)
  else:
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  return render_template('pages/home.html')

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  data = []
  shows = Show.query.order_by('start_time').all()
  for show in shows:
    show_dict = dict()
    show_dict['venue_id'] = show.venue_id

    venue = Venue.query.get(show.venue_id)
    show_dict['venue_name'] = venue.name

    show_dict['artist_id'] = show.artist_id

    artist = Artist.query.get(show.artist_id)
    show_dict['artist_name'] = artist.name
    show_dict['artist_image_link'] = artist.image_link

    show_dict['start_time'] = str(show.start_time)

    data.append(show_dict)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error = False
  try:
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    start_time = request.form['start_time']

    show = Show(
      artist_id=artist_id,
      venue_id=venue_id,
      start_time=start_time
    )
    db.session.add(show)
    db.session.commit()
  except:
    error = True
    db.session.rollback()
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Show could not be listed.')
  else:
    flash('Show was successfully listed!')
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
