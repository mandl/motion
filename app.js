/*
	Heizung

	Copyright (C) 2018-2021 Mandl

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

const fs = require('fs');
const express = require('express');
const path = require('path');
const jsonBody = require('body/json');
const bodyParser = require('body-parser');
const cv = require('opencv4nodejs');
const { logger, logfolder } = require('./logger');
const configFileName = './config.json'
const configData = require(configFileName);

const showImageCount = 99;
var dayFolder;
var recentIndex = 0;


var handlebars = require('express-handlebars')
	.create({
		defaultLayout: 'main',
		helpers: {
			section: function (name, options) {
				if (!this._sections) {
					this._sections = {};
				}
				this._sections[name] = options.fn(this);
				return null;
			},
			// 2018-05-30_17_15_53.396682.jpg
			formatTimeTwc: function (strTime) {
				strTime = strTime.toString();
				return strTime.substr(0, 10) + '    ' + strTime.substr(11, 8).replace(/_/g, ':');
			}
		}
	});


// Create a new Express application.
var app = express();

app.disable('x-powered-by');

// Use application-level middleware for common functionality, including
// logging, parsing, and session handling.
//app.use(require('morgan')('dev'));
app.use(require('cookie-parser')());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(require('express-session')({
	secret: 'keyboard cat',
	resave: false,
	saveUninitialized: false
}));

// static routes
app.use(express.static(__dirname + '/public'));

var files = fs.readdirSync(path.join(__dirname, 'picture', 'motion'));
dayFolder = files[files.length - 1];

logger.info(dayFolder);

app.use('/picture', express.static(__dirname + '/picture', { maxAge: '30 days' }))

// view engine
app.engine('handlebars', handlebars.engine);
app.set('view engine', 'handlebars');


// renter main page
app.get('/', function (req, res) {

	res.render('live', { layout: 'main', title: 'Live view', camname: 'cam1' });

});

// renter main page
app.get('/cam1view', function (req, res) {

	res.render('live', { layout: 'main', title: 'Live view', camname: 'cam1' });

});

//renter cam page
app.get('/cam2view', function (req, res) {

	res.render('live', { layout: 'main', title: 'Live view', camname: 'cam2' });

});

//renter cam page
app.get('/cam3view', function (req, res) {

	res.render('live', { layout: 'main', title: 'Live view', camname: 'cam3' });

});

// renter log page
app.get('/log', function (req, res) {
	var logtext = fs.readFileSync(logfolder(), 'utf8')
	logtext = logtext.replace(/\n/g, '<br>');

	res.render('logfile', { layout: 'main', title: 'Log', logdata: logtext });

});

// renter admin page
app.get('/admin', function (req, res) {

	let rawdata = fs.readFileSync(configFileName);
	let configData = JSON.parse(rawdata);
	console.log(configData);
	res.render('admin', { layout: 'main', title: 'Admin', level: configData.level, area: configData.area, threshold: configData.threshold });

});

// admin data
app.post('/admindata', function (req, res) {

	var annotate = req.body.annotate;
	var level = req.body.level;
	var threshold = req.body.threshold;
	var area = req.body.area;

	logger.info('admindata');
	console.log(annotate, level, threshold, area)
	configData.level = Number(level)
	configData.threshold = Number(threshold)
	configData.area = Number(area)
	if (annotate === 'On') {
		configData.annotate = true
	}
	else {
		configData.annotate = false
	}
	fs.writeFileSync(configFileName, JSON.stringify(configData))

	res.redirect('/motion');
});

// render motion page
app.get('/motion', function (req, res) {
	var day = req.query.day;
	var index = req.query.index;
	var n = 0;
	if (day == null) {
		day = dayFolder;
	}
	else {
		dayFolder = day;
	}
	if (index == null) {
		index = recentIndex;
	}
	else {
		recentIndex = index;
	}
	n = index * showImageCount;
	try {
		var files = fs.readdirSync(path.join(__dirname, 'picture', 'motion', day));
		var pagiCount = files.length / showImageCount;
		var motionFiles = { "data": [] };
		var FileCount = files.length;
		var minFiles = files.slice(n, n + showImageCount);
		for (i in minFiles) {
			var me = { "name": minFiles[i], "folder": day };
			motionFiles.data.push(me);
		}
		var nextIndex = parseInt(index, 10) + 1;
		var prevIndex = parseInt(index, 10) - 1;
		res.render('motion', { layout: 'main', title: 'Motion', fileNames: motionFiles, fileCount: FileCount, fileStart: n, fileStop: n + showImageCount, day: day, index: nextIndex, prevIndex: prevIndex, pagiCount: pagiCount });
	}
	catch (e) {
		res.render('motion', { layout: 'main', title: 'Motion' });
	}
});


// Clear all pictures
app.get('/motiondelete', function (req, res) {

	var day = req.query.day;
	if (day !== null) {
		try {

			if (fs.existsSync(path.join(__dirname, 'picture', 'motion', day))) {
				fs.readdir(path.join(__dirname, 'picture', 'motion', day), (err, files) => {
					if (err) throw err;

					for (const file of files) {
						fs.unlinkSync(path.join(__dirname, 'picture', 'motion', day, file));
					}
					fs.rmdirSync(path.join(__dirname, 'picture', 'motion', day))
					res.redirect('/motion/motiondays');
				});
			}
		}
		catch (ex) {
			logger.error(ex);
		}
	}

});


// Clear video
app.get('/videodelete', function (req, res) {
	var day = req.query.day;
	if (day !== null) {
		try {
			if (fs.existsSync(path.join(__dirname, '..', 'disk', 'video', 'backup', day))) {
				fs.unlinkSync(path.join(__dirname, '..', 'disk', 'video', 'backup', day))
				logger.info('Delete ' + day)
				res.redirect('/motion/videoview');
			}
		}
		catch (ex) {
			logger.error(ex);
		}
	}
});

// Clear all video files
app.get('/videodeleteall', function (req, res) {

	try {

		directory = path.join(__dirname, '..', 'disk', 'video', 'backup');
		fs.readdir(directory, (err, files) => {
			if (err) throw err;
			for (const file of files) {
				fs.unlink(path.join(directory, file), err => {
					if (err) throw err;
				});
			}
		});
		logger.info('Delete alls videos');
		res.redirect('/motion/videoview');
	}
	catch (ex) {
		logger.error(ex);
	}

});



// render motion days page
app.get('/motiondays', function (req, res) {

	var files = fs.readdirSync(path.join(__dirname, 'picture', 'motion'));
	var motionFiles = { "data": [] };
	for (i in files) {
		var me = { "name": files[i] };
		motionFiles.data.push(me);
	}

	// console.log(motionFiles);
	res.render('motiondays', { layout: 'main', title: 'Days', fileNames: motionFiles });
});


// render motion days page
app.get('/videoview', function (req, res) {

	//var files = fs.readdirSync(path.join(__dirname,'picture','motion'));
	var files = fs.readdirSync(path.join(__dirname, '..', 'disk', 'video', 'backup'));

	var motionFiles = { "data": [] };
	for (i in files) {
		var me = { "name": files[i] };
		motionFiles.data.push(me);
	}

	// console.log(motionFiles);
	res.render('video', { layout: 'main', title: 'Video', fileNames: motionFiles });
});



// render motion days page
app.get('/motiondaysdelete', function (req, res) {


	var files = fs.readdirSync(path.join(__dirname, 'picture', 'motion'));
	var motionFiles = { "data": [] };
	for (i in files) {
		var me = { "name": files[i] };
		motionFiles.data.push(me);
	}

	// console.log(motionFiles);
	res.render('motiondeletedays', { layout: 'main', title: 'Days', fileNames: motionFiles });
});


function updateImage(x, y, h, w, name) {


	const mat = cv.imread(__dirname + '/picture/config/view/' + name + '.png');

	mat.drawRectangle(new cv.Point(x, y), new cv.Point(x + w, y + h), new cv.Vec(255, 0, 0), 8);

	cv.imwrite(__dirname + '/picture/config/view/' + name + '.png', mat);

}


// save new ROI
app.get('/save', function (req, res) {

	var cam = req.query.cam;
	var startX = req.query.startX;
	var startY = req.query.startY;
	var w = req.query.w;
	var h = req.query.h;

	if ((startX != null) && (startY != null) && (w != null) && (h != null)) {
		//console.log(cam,startX,startY,w,h);
		if (cam == "cam1") {
			configData.cam1.x = parseInt(startX, 10)
			configData.cam1.y = parseInt(startY, 10)
			configData.cam1.h = parseInt(h, 10)
			configData.cam1.w = parseInt(w, 10)
			fs.writeFileSync(configFileName, JSON.stringify(configData, null, 4))
			updateImage(configData.cam1.x, configData.cam1.y, configData.cam1.h, configData.cam1.w, cam)
		}
		if (cam == "cam2") {
			configData.cam2.x = parseInt(startX, 10)
			configData.cam2.y = parseInt(startY, 10)
			configData.cam2.h = parseInt(h, 10)
			configData.cam2.w = parseInt(w, 10)
			fs.writeFileSync(configFileName, JSON.stringify(configData, null, 4))
			updateImage(configData.cam2.x, configData.cam2.y, configData.cam2.h, configData.cam2.w, cam)

		}
		if (cam == "cam3") {
			configData.cam3.x = parseInt(startX, 10)
			configData.cam3.y = parseInt(startY, 10)
			configData.cam3.h = parseInt(h, 10)
			configData.cam3.w = parseInt(w, 10)
			fs.writeFileSync(configFileName, JSON.stringify(configData, null, 4))
			updateImage(configData.cam3.x, configData.cam3.y, configData.cam3.h, configData.cam3.w, cam)
		}
	}
	res.send('ok');
	res.end();
});

// set motion day
app.get('/setmotiondays', function (req, res) {

	dayFolder = req.query.day;
	res.send('ok');
	res.end();
});

// delete log
app.get('/deleteLog', function (req, res) {

	fs.writeFileSync(logfolder(), "");
	res.send('ok');
	res.end();
});

// Handle 404
app.use(function (req, res, next) {
	res.redirect('/');

});

app.listen(3000, function () {
	logger.info('Motion listening on port 3000!');
});


