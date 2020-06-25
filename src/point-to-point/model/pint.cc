#include <cmath>
#include <cstdlib>
#include <cstdio>

#include "pint.h"

namespace ns3{

double Pint::log_base = 1.05;
double Pint::log_factor = 1 / log(log_base);

void Pint::set_log_base(double base){
	log_base = base;
	log_factor = 1 / log(log_base);
}

uint16_t Pint::encode_u(double u){
	uint32_t u_1k = ceil(u * multiple);
	if (u_1k == 0) u_1k = 1;
	double power = log(u_1k) * log_factor;
	uint16_t p_upper = ceil(power), p_lower = floor(power);
	double upper = pow(log_base, p_upper), lower = pow(log_base, p_lower);
	if (p_upper == p_lower)
		upper *= log_base;
	uint16_t p = (rand() % 65536 < (u_1k - lower) / (upper - lower) * 65536) ? p_upper : p_lower;
	return p;
}

double Pint::decode_u(uint16_t p){
	return pow(log_base, p) / multiple;
}

} /* namespace ns3 */
