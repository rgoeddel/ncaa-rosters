(function() {
    // Prevent crazy redraw updates on resize
    d3.select(window).on('resize', throttle);

    var zoom = d3.behavior.zoom()
        .scaleExtent([1, 20])
        .on('zoom', move);

    var width = document.getElementById('container').offsetWidth;
    var height = width / 2;

    var loadCount = 2; // XXX So hacky. Needs to be updated lots. FIX
    var topoC, topoS, topoP, projection, path, svg, g;
    var graticule = d3.geo.graticule();

    // XXX Tooltips later?

    setup(width, height);

    function setup(width, height) {
        projection = d3.geo.mercator()
            .translate([0, 0])
            .scale(width / 2 / Math.PI);

        path = d3.geo.path()
            .projection(projection);

        svg = d3.select('#container').append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', 'translate('+width/2+','+height/2+')')
            .call(zoom)

        g = svg.append('g');
    }

    d3.json('geo/world-50m.json', function(error, world) {
        if (error) throw error;

        var countries = topojson.feature(world,
                                         world.objects.countries);
        topoC = countries.features;

        loadCount = loadCount - 1;
        if (loadCount <= 0)
            draw(topoC, topoS, topoP);
    });

    d3.json('geo/states.json', function(error, us) {
        if (error) throw error;

        var states = topojson.feature(us, us.objects.states);
        topoS = states.features;

        loadCount = loadCount - 1;
        if (loadCount <= 0)
            draw(topoC, topoS, topoP);
    });

    //d3.json('geo/test-provinces.json', function(error, canada) {
    //    if (error) throw error;

    //    var provinces = topojson.feature(canada, canada.objects.provinces);
    //    topoP = provinces.features;
    //    console.log(topoP);

    //    loadCount = loadCount - 1;
    //    if (loadCount <= 0)
    //        draw(topoC, topoS, topoP);
    //});

    function draw(topoC, topoS, topoP) {
        // Draw in countries
        var country = g.selectAll('.country').data(topoC);
        country.enter().insert('path')
            .attr('class', 'country')
            .attr('d', path)
            .attr('id', function(d,i) { return d.id; })
            .style('fill', '#aaa')
            .style('stroke', '#000');

        // Draw in states
        var state = g.selectAll('.state').data(topoS);
        state.enter().insert('path')
            .attr('class', 'state')
            .attr('d', path)
            .style('fill', 'none')
            .style('stroke', '#000');
    }

    function redraw() {
        width = document.getElementById('container').offsetWidth;
        height = width / 2;
        d3.select('svg').remove();
        setup(width, height);
        draw(topoC, topoS, topoP);
    }

    function move() {
        var t = d3.event.translate;
        var s = d3.event.scale;
        var h = height / 3;

        t[0] = Math.min((width / 2) * (s - 1),
                        Math.max((width / 2) * (1 - s), t[0]));
        t[1] = Math.min((height / 2) * (s-1) + (h * s),
                        Math.max((height / 2) * (1 - s) - (h * s), t[1]));

        zoom.translate(t);
        g.style('stroke-width', 1/s)
            .attr('transform', 'translate(' + t + ')scale(' + s + ')');
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
    // Roster callback. This takes the roster index we build and
    // uses it to populate our comparison tool
    function rosterCallback(rosterPages) {
        console.log(rosterPages);
    };

    // Build roster index
    var rosterPages = [];
    d3.html('test-rosters', function(e, d) {
        var lis = d3.select(d).selectAll('li').selectAll('a');
        lis.forEach(function(v) {
            rosterPages.push(v[0].text)
        });

        rosterCallback(rosterPages);
    });
})();
