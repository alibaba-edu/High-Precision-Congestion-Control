/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Author: John Abraham <john.abraham@gatech.edu>
 */

#include "winport.h"
#include <cmath>
#include <string>
#include "ns3/log.h"
#include "ns3/assert.h"

#if 0
long double fabs (int v);
long double sqrt (uint64_t v);
long double sqrt (uint16_t v);
long double sqrt (unsigned int v);
long double log10 (int v);
double erfc (double v);
bool isblank (char v);
long double ceil (uint32_t v);
long double abs (uint32_t v);










long double 
log2 (uint32_t v)
{
	//std::cout << "log2" << std::endl;
	return log (static_cast<double> (v)/log (2.0));
}

/*
long double 
log2 (double v)
{
	//std::cout << "log2" << std::endl;
	return log(v)/log(2.0);
}
*/
long double 
log2 (long double v)
{
	//std::cout << "log2" << std::endl;
	return log(v)/log(2.0);
}
/*
uint32_t 
round (double v)
{
	//std::cout << "round" << std::endl;
  if(v>=0)
    {
	  return uint32_t (((v-floor(v) >= 0.5) ? ceil(v):floor(v))) ;
    }
  else
    {
	  NS_ASSERT ("Not yet implemented");
	  return -1;
    }
}

int64_t 
lround (double v)
{
	//std::cout << "lround" << std::endl;
  if(v>=0)
    {
	  return ((v-floor(v) >= 0.5) ? ceil(v):floor(v)) ;
    }
  else
    {
	  NS_ASSERT ("Not yet implemented");
	  return -1;
    }
}
uint64_t 
lrint (double v)
{
  if(v>=0)
    {
	  return ((v-floor(v) >= 0.5) ? ceil(v):floor(v)) ;
    }
  else
    {
	  NS_ASSERT ("Not yet implemented");
	  return -1;
    }
}
*/
long double 
pow (uint32_t u,uint32_t v)
{
	//std::cout << "pow" << std::endl;
  return pow (static_cast<double> (u), static_cast<int> (v));
}

long double 
pow (double u,uint32_t v)
{
	//std::cout << "pow" << std::endl;
  return pow (u, static_cast<int> (v));
}

long double 
pow (int u, double v)
{
	//std::cout << "pow" << std::endl;
  return pow (static_cast<double> (u), v);
}

long double 
pow (int u, uint32_t v)
{  
	//std::cout << "pow" << std::endl;
  return pow (static_cast<double> (u), static_cast<int> (v));
}

long double 
pow (int u, int v)
{  
	//std::cout << "pow" << std::endl;
  return pow (static_cast<double> (u), v);
}

long double 
pow (int u, long double v)
{
	//std::cout << "pow" << std::endl;
  return pow (static_cast<long double> (u),v);
}

long double 
fabs (int v)
{
	//std::cout << "fabs" << std::endl;
  return fabs (static_cast<double> (v));
}

long double 
sqrt (uint64_t v)
{
	//std::cout << "sqrt" << std::endl;
  return sqrt (static_cast<double> (v));
}

long double 
sqrt (uint16_t v)
{
	//std::cout << "sqrt" << std::endl;
  return sqrt (static_cast<double> (v));
}

long double 
sqrt (unsigned int v)
{
	//std::cout << "sqrt" << std::endl;
  return sqrt (static_cast<double> (v));
}

long double 
log10 (int v)
{
	//std::cout << "log10" << std::endl;
	return log10 (static_cast<double> (v));
}

long double 
ceil (uint32_t v)
{
	//std::cout << "ceil" << std::endl;
  return ceil (static_cast<double> (v));  
}

long double 
abs (uint32_t v)
{
	//std::cout << "abs" << std::endl;
  return abs (static_cast<double> (v));  
}
//double erfc (double v);
bool 
isblank (char v)
{
	//std::cout << "isblank" << std::endl;
  return isspace (v);
}

#endif