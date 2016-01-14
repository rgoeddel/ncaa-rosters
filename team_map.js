(function() {
    // Prevent crazy redraw updates on resize
    d3.select(window).on('resize', throttle);

    var zoom = d3.behavior.zoom()
        .scaleExtent([1, 20])
        .on('zoom', move);

    var width = document.getElementById('container').offsetWidth;
    var height = width / 2;

    var drawData = {};
    var projection, path, svg, g;
    var graticule = d3.geo.graticule();

    var rosters = [];

    setup(width, height);

    function setup(width, height) {
        projection = d3.geo.mercator()
            .translate([width/2, height/2])
            .scale(width / 2 / Math.PI);

        path = d3.geo.path()
            .projection(projection);

        svg = d3.select('#container').append('svg')
            .attr('width', width)
            .attr('height', height)
            .call(zoom)
            .append('g');

        g = svg.append('g');
    }

    d3.json('geo/world-50m.json', function(error, world) {
        if (error) throw error;

        var countries = topojson.feature(world,
                                         world.objects.countries);
        drawData['countries'] = countries.features;
        draw(drawData);
    });

    d3.json('geo/states.json', function(error, us) {
        if (error) throw error;

        var states = topojson.feature(us, us.objects.states);

        drawData['states'] = states.features;
        draw(drawData);
    });

    //d3.json('geo/test-provinces.json', function(error, canada) {
    //    if (error) throw error;

    //    var provinces = topojson.feature(canada, canada.objects.provinces);
    //    drawData['provinces'] = provinces.features;
    //    draw(drawData);
    //});
    function colorStringInverse(colorString) {
        var rgb = d3.rgb(colorString);
        rgb.r = 255 - rgb.r;
        rgb.g = 255 - rgb.g;
        rgb.b = 255 - rgb.b;

        return rgb.toString();
    }

    function draw(drawData) {
        // Draw in countries
        if (drawData['countries']) {
            var country = g.selectAll('.country').data(drawData['countries']);
            country.enter().insert('path')
                .attr('class', 'country')
                .attr('d', path)
                .attr('id', function(d,i) { return d.id; });
        }

        // Draw in states
        // XXX State borders more accurate than coastlines of world
        if (drawData['states']) {
            var state = g.selectAll('.state').data(drawData['states']);
            state.enter().insert('path')
                .attr('class', 'state')
                .attr('d', path);
        }

        // Draw in provinces XXX (json files needed)

        // Draw in roster dots
        if (drawData['roster']) {
            // Marshall hometown data. Calculate a compl. color for borders.
            // It would be ideal to have the secondary color of the school,
            // but this wasn't scrapable...
            var roster = drawData['roster'];
            var hometowns = [];
            for (var key in roster.hometowns) {
                hometowns.push(roster.hometowns[key]);
            }

            var player = g.selectAll('.player').data(hometowns);
            player.enter().insert('circle');

            player
                .attr('class', 'player')
                .attr('d', path)
                .attr('cx', function(d) { return projection([d.lon, d.lat])[0]; })
                .attr('cy', function(d) { return projection([d.lon, d.lat])[1]; })
                .attr('r', function(d) { return .3*Math.sqrt(d.count); })
                .attr('fill', roster.color)
                .attr('stroke', colorStringInverse(roster.color))
                .attr('stroke-width', .1);

            player.exit().remove();
        }
    }

    function redraw() {
        width = document.getElementById('container').offsetWidth;
        height = width / 2;
        d3.select('svg').remove();
        setup(width, height);
        draw(drawData);
    }

    function move() {
        var t = d3.event.translate;
        var s = d3.event.scale;
        zscale = s;
        var h = height / 4;

        t[0] = Math.min((width / height) * (s - 1),
                        Math.max(width * (1 - s), t[0]));
        t[1] = Math.min(h * (s-1) + (h * s),
                        Math.max(height * (1 - s) - (h * s), t[1]));

        zoom.translate(t);
        g.attr('transform', 'translate(' + t + ')scale(' + s + ')');

        d3.selectAll('.country')
            .style('stroke-width', .5/s);
        d3.selectAll('.state')
            .style('stroke-width', .5/s);
        d3.selectAll('.player')
            .style('stroke-width', .5/s);
    }

    // Delay redraws
    var throttleTimer;
    function throttle() {
        window.clearTimeout(throttleTimer);
        throttleTimer = window.setTimeout(function() {
            redraw();
        }, 200);
    }

    // ==================================
    function saveRoster(roster) {
        rosters.push(roster);
        updateIndex(rosters);
    }

    function updateIndex(rosters) {
        // Make selector tool
        var sel = d3.selectAll('form').selectAll('select');
        sel.on('click', selectChanged);

        var opts = sel.selectAll('option')
            .data(rosters)
            .enter().append('option')
            .attr('value', function (d) { return d.name; })
            .text(function(d) { return d.name; });
    };

    function selectChanged() {
        var sel = document.getElementById('teams');
        var idx = sel.selectedIndex;
        var team = sel.options[sel.selectedIndex].value;

        drawData['roster'] = rosters[idx];
        draw(drawData);
    };

    // Build roster index
    d3.html('rosters', function(e, d) {
        var lis = d3.select(d).selectAll('li').selectAll('a');
        lis.forEach(function(v) {
            d3.json('rosters/'+v[0].text, saveRoster);
        });
    });
})();
