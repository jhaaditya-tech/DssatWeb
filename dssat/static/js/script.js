var map = L.map('map');
var adm1='';
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
function ajax_call(ajax_url, ajax_data) {
    //update database
    console.log(ajax_data);
    return $.ajax({
        type: "POST",
        headers: {'X-CSRFToken': getCookie('csrftoken')},
        url: ajax_url.replace(/\/?$/, '/'),
        dataType: "json",
        data: ajax_data
    })
        .fail(function (xhr, status, error) {
        });
}
function whenClicked(e) {
   var admin1= e.target.feature.properties.ADM1_EN;
   adm1=admin1;
   document.getElementById('adm1').innerHTML=admin1;
   chart.setTitle({text:'Observed and Simulated Yield for the baseline scenario in '+admin1});
   // window.location.hash = "#testing";

      $('html,body').animate({
        scrollTop: $("#testing").offset().top},
        'slow');
 const xhr = ajax_call("run-spatial-dssat", {
     'dbname':'dssatserv',
        'schema':'kenya',
     'admin1':admin1,
     'plantingdate':'2021-03-15',
     'cultivar':'Short',
     'nitrogen':30.0

 });
    xhr.done(function (result) {
        console.log(result);
    });
}
function onEachFeature(feature, layer) {

    //bind click
    layer.on({
        click: whenClicked
    });
}
var  country_layer = L.geoJSON(shp_obj, {
                style: {
                    weight: 2,
                    opacity: 1,
                    color: '#000000',  //Outline color
                    fillOpacity: 0.2,
                     strokeWidth: 0,
                },
        onEachFeature: onEachFeature,
                // onEachFeature: onEachFeature_country,
            });

            country_layer.addTo(map);
            map.fitBounds(country_layer.getBounds());

    var chart = new Highcharts.Chart({

    chart: {
        renderTo: 'chart'
    },

    yAxis: {
        labels: {
            formatter: function() {
                return this.value +' km';
            }
        }
    },

    series: [{
        data: []
    }]

});
