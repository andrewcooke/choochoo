#!/bin/sh
# script generated by
# > ch2 kit dump --cmd ch2
ch2 kit delete --force bike
ch2 kit start --force bike cotic 2017-01-01
ch2 kit change --force cotic chain pc1110 2019-10-11
ch2 kit start --force bike bowman 2019-11-01
ch2 kit change --force bowman front-wheel carbonfan 2019-11-01
ch2 kit change --force bowman rear-wheel carbonfan 2019-11-01
ch2 kit change --force bowman front-tyre schwalbe-pro-1 2019-11-01
ch2 kit change --force bowman rear-tyre schwalbe-pro-1 2019-11-01
ch2 kit change --force bowman chain kmc-x11 2019-11-01
ch2 kit change --force bowman chainset fsa-slk 2019-11-01
ch2 kit change --force bowman front-derailleur sram-force-fd 2019-11-01
ch2 kit change --force bowman rear-derailleur shimano-xt-rd 2019-11-01
ch2 kit change --force bowman cassette hope-40 2019-11-01
ch2 kit change --force bowman cassette-large hope-40 2019-11-01
ch2 kit change --force bowman brake-cables jagwire-pro-brake 2019-11-01
ch2 kit change --force bowman gear-cables jagwire-pro-gear 2019-11-01
ch2 kit change --force bowman front-pads spyre-pad 2019-11-01
ch2 kit change --force bowman rear-pads spyre-pad 2019-11-01
ch2 kit change --force bowman front-sealant stans 2019-11-16
ch2 kit change --force bowman rear-sealant stans 2019-11-16
ch2 kit change --force bowman chain kmc-x11el '2020-03-21 21:07:33'
ch2 kit change --force bowman front-pads disco-pad 2021-03-01
ch2 kit change --force bowman rear-pads disco-pad 2021-03-01
ch2 kit change --force bowman chain fsa 2021-04-01
ch2 kit change --force bowman front-tyre pirelli-p-zero 2021-08-09
ch2 kit change --force bowman rear-tyre pirelli-p-zero 2021-08-09
ch2 kit change --force cotic chain kmc-x11el 2020-10-18
ch2 kit start --force bike cbutler 2019-01-01
ch2 kit rebuild
